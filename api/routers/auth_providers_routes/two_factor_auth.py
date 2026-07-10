import pyotp
import qrcode
import io
import base64
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from operations.fb_operations.users_crud import check_apikey_exists
from operations.fb_operations.end_users_crud import get_end_user_by_email, create_end_user, update_end_user
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
    email: EmailStr

class VerifySetup2FASchema(BaseModel):
    client_id: str
    client_secret: str
    email: EmailStr
    code: str

class Verify2FASchema(BaseModel):
    client_id: str
    client_secret: str
    email: EmailStr
    code: str

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


# 1. Setup 2FA: Create/retrieve a secret, generate QR code URL & Base64 QR code image
@router.post("/auth/2fa/setup")
async def setup_2fa(inp: Setup2FASchema):
    config = validate_client_credentials(inp.client_id, inp.client_secret)
    brand_name = config.get("ui", {}).get("brand_name", "DeB-Auth")

    # Get or create end user
    end_user = get_end_user_by_email(inp.client_id, inp.email)
    if not end_user:
        # Create a skeleton end user record
        end_user = EndUser(
            id=inp.email,
            email=inp.email,
            created_at=time.time(),
            custom_fields={}
        )
        create_end_user(inp.client_id, end_user)

    # Generate or get TOTP secret
    custom_fields = end_user.custom_fields or {}
    totp_secret = custom_fields.get("totp_secret")
    if not totp_secret:
        totp_secret = pyotp.random_base32()
        custom_fields["totp_secret"] = totp_secret
        custom_fields["totp_enabled"] = False # Not fully verified/enabled yet
        end_user.custom_fields = custom_fields
        update_end_user(inp.client_id, end_user)

    # Generate provisioning URI
    totp = pyotp.TOTP(totp_secret)
    provisioning_uri = totp.provisioning_uri(name=inp.email, issuer_name=brand_name)

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
        "secret": totp_secret,
        "provisioning_uri": provisioning_uri,
        "qr_code_base64": f"data:image/png;base64,{qr_base64}"
    }

# 2. Verify 2FA Setup: Enter the first code to verify and enable 2FA permanently
@router.post("/auth/2fa/setup/verify")
async def setup_verify_2fa(inp: VerifySetup2FASchema):
    validate_client_credentials(inp.client_id, inp.client_secret)
    
    end_user = get_end_user_by_email(inp.client_id, inp.email)
    if not end_user or "totp_secret" not in (end_user.custom_fields or {}):
        raise HTTPException(status_code=400, detail="2FA setup not initiated for this email")

    totp_secret = end_user.custom_fields["totp_secret"]
    totp = pyotp.TOTP(totp_secret)
    
    if not totp.verify(inp.code):
        raise HTTPException(status_code=422, detail="Invalid time-based verification code")

    # Mark 2FA as fully enabled
    end_user.custom_fields["totp_enabled"] = True
    update_end_user(inp.client_id, end_user)

    return {
        "success": True,
        "message": "Two-Factor Authentication (2FA) enabled successfully"
    }

# 3. Verify 2FA Route: Verify a code for subsequent logins
@router.post("/auth/2fa/verify")
async def verify_2fa(inp: Verify2FASchema):
    validate_client_credentials(inp.client_id, inp.client_secret)
    
    end_user = get_end_user_by_email(inp.client_id, inp.email)
    if not end_user or not (end_user.custom_fields or {}).get("totp_enabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled for this email")

    totp_secret = end_user.custom_fields["totp_secret"]
    totp = pyotp.TOTP(totp_secret)
    
    if not totp.verify(inp.code):
        raise HTTPException(status_code=422, detail="Invalid time-based verification code")

    return {
        "success": True,
        "message": "Verification successful"
    }
