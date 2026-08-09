import pyotp
import qrcode
import io
import base64
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from operations.fb_operations.users_crud import check_apikey_exists
from operations.fb_operations.end_users_crud import get_end_user_by_identifier, create_end_user, update_end_user
from schemas.db_schemas.end_user_schema import EndUser
from operations.redis_operations.handlers import redis_set, redis_get, redis_unlink
from api.dependencies.auth_state import get_and_validate_auth_state
from utils.redirectcode_genereator import generate_redirect_code
import time

router = APIRouter(
    tags=["Two-Factor (2FA) Authentication / TOTP"]
)

# Schemes
class Setup2FASchema(BaseModel):
    client_id: str
    client_secret: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None

class VerifySetup2FASchema(BaseModel):
    client_id: str
    client_secret: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    code: str

class Verify2FASchema(BaseModel):
    client_id: str
    client_secret: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    code: str

def get_user_identifier(inp) -> str:
    identifier = inp.email or inp.mobile_number
    if not identifier or not str(identifier).strip():
        raise HTTPException(
            status_code=400, 
            detail="Either 'email' or 'mobile_number' is required to identify the user for 2FA"
        )
    return str(identifier).strip()

# Helper to validate client credentials
def validate_client_credentials(client_id: str, client_secret: str):
    config = check_apikey_exists(client_id)
    if not config:
        raise HTTPException(status_code=403, detail="Invalid Client ID")
    
    # Ensure Two-Factor Authentication is enabled for the project
    two_factor_config = config.get("two_factor", {})
    if not two_factor_config.get("enabled", False):
        raise HTTPException(
            status_code=403,
            detail="Two-Factor Authentication (2FA) is disabled for this project"
        )
    # Retrieve project owner user to check the secret
    from operations.fb_operations.users_crud import get_all_users
    users = get_all_users()
    matched = False
    
    # get_all_users() returns a dict where keys are email_keys and values are user dicts
    user_list = users.values() if isinstance(users, dict) else (users or [])
    
    for u in user_list:
        if isinstance(u, dict):
            secrets = u.get("secrets", {})
            if secrets.get(client_id) == client_secret:
                matched = True
                break
    if not matched:
        raise HTTPException(status_code=403, detail="Invalid Client Secret")
    return config


# 1. Setup 2FA: Create/retrieve a domain-scoped secret, generate QR code URL & Base64 QR code image
@router.post("/auth/2fa/setup")
async def setup_2fa(inp: Setup2FASchema):
    config = validate_client_credentials(inp.client_id, inp.client_secret)
    brand_name = config.get("ui", {}).get("brand_name", "DeB-Auth")
    user_identifier = get_user_identifier(inp)

    # Retrieve or create domain-scoped end user record (tied to client_id + user_identifier)
    end_user = get_end_user_by_identifier(inp.client_id, user_identifier)
    if not end_user:
        end_user = EndUser(
            id=user_identifier,
            email=inp.email if inp.email else None,
            mobile_number=inp.mobile_number if inp.mobile_number else None,
            created_at=time.time(),
            custom_fields={"domain_client_id": inp.client_id}
        )
        create_end_user(inp.client_id, end_user)

    # Generate or get TOTP secret scoped specifically to this product domain (client_id)
    custom_fields = end_user.custom_fields or {}
    totp_secret = custom_fields.get("totp_secret")
    if not totp_secret:
        totp_secret = pyotp.random_base32()
        custom_fields["totp_secret"] = totp_secret
        custom_fields["totp_enabled"] = False # Not fully verified/enabled yet
        custom_fields["domain_client_id"] = inp.client_id
        end_user.custom_fields = custom_fields
        update_end_user(inp.client_id, end_user)

    # Generate provisioning URI with brand name
    totp = pyotp.TOTP(totp_secret)
    provisioning_uri = totp.provisioning_uri(name=user_identifier, issuer_name=brand_name)

    # Generate QR Code Image (base64 encoded)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {
        "success": True,
        "user_identifier": user_identifier,
        "secret": totp_secret,
        "provisioning_uri": provisioning_uri,
        "qr_code_base64": f"data:image/png;base64,{qr_base64}"
    }

# 2. Verify 2FA Setup: Enter the first code to verify and enable 2FA permanently for this domain
@router.post("/auth/2fa/setup/verify")
async def setup_verify_2fa(inp: VerifySetup2FASchema):
    validate_client_credentials(inp.client_id, inp.client_secret)
    user_identifier = get_user_identifier(inp)

    end_user = get_end_user_by_identifier(inp.client_id, user_identifier)
    if not end_user or "totp_secret" not in (end_user.custom_fields or {}):
        raise HTTPException(status_code=400, detail=f"2FA setup not initiated for '{user_identifier}' on this domain")

    totp_secret = end_user.custom_fields["totp_secret"]
    totp = pyotp.TOTP(totp_secret)
    
    if not totp.verify(inp.code):
        raise HTTPException(status_code=422, detail="Invalid time-based verification code")

    # Mark 2FA as fully enabled for this product domain
    end_user.custom_fields["totp_enabled"] = True
    update_end_user(inp.client_id, end_user)

    return {
        "success": True,
        "user_identifier": user_identifier,
        "message": f"Two-Factor Authentication (2FA) enabled successfully for '{user_identifier}' on this product domain"
    }

# 3. Verify 2FA Route: Verify a code for subsequent logins
@router.post("/auth/2fa/verify")
async def verify_2fa(inp: Verify2FASchema):
    validate_client_credentials(inp.client_id, inp.client_secret)
    user_identifier = get_user_identifier(inp)

    end_user = get_end_user_by_identifier(inp.client_id, user_identifier)
    if not end_user or not (end_user.custom_fields or {}).get("totp_enabled"):
        raise HTTPException(status_code=400, detail=f"2FA is not enabled for '{user_identifier}' on this domain")

    totp_secret = end_user.custom_fields["totp_secret"]
    totp = pyotp.TOTP(totp_secret)
    
    if not totp.verify(inp.code):
        raise HTTPException(status_code=422, detail="Invalid time-based verification code")

    return {
        "success": True,
        "user_identifier": user_identifier,
        "message": "Verification successful"
    }
