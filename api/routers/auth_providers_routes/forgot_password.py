from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, EmailStr
from operations.redis_operations.handlers import redis_set, redis_get, redis_unlink
from api.dependencies.auth_state import get_and_validate_auth_state
from services.email_service import main as email_main
from services.email_service import forgot_password_email
from utils.redirectcode_genereator import generate_redirect_code
import secrets
import os

router = APIRouter(
    tags=["Forgot Password"]
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class ForgotPasswordSendSchema(BaseModel):
    request_id: str
    email: EmailStr


class ForgotPasswordResetSchema(BaseModel):
    token: str
    new_password: str
    confirm_password: str


@router.post("/auth/forgot-password/send")
async def forgot_password_send(inp: ForgotPasswordSendSchema, request: Request, bgt: BackgroundTasks):
    state = await get_and_validate_auth_state(request, inp.request_id, required_step="device_validation")

    # Check that password auth is enabled
    raw_methods = state.config.get('auth_methods', [])
    pwd_method = next((m for m in raw_methods if m.get('id') == 'password' and m.get('enabled')), None)
    if not pwd_method:
        raise HTTPException(status_code=400, detail="Password authentication is not enabled for this project")

    # Check if forgot password is enabled in config
    if not state.config.get('forgot_password_enabled', True):
        raise HTTPException(status_code=400, detail="Forgot password is not enabled for this project")

    # Generate a secure reset token
    reset_token = secrets.token_urlsafe(48)

    # Store reset data in Redis (15 min expiry)
    reset_data = {
        'email': inp.email,
        'request_id': inp.request_id,
        'client_id': state.client_id,
        'config': state.config,
    }
    await redis_set(key=f"reset:{reset_token}", value=reset_data, exp=900)  # 15 minutes

    # Build reset link
    reset_link = f"{FRONTEND_URL}/auth/reset-password/{reset_token}"

    # Get brand name from config
    brand_name = state.config.get('ui', {}).get('brand_name', 'DeB-Auth')

    # Send email in background
    email_content = forgot_password_email.generate_forgot_password_email_content(
        reset_link=reset_link,
        brand_name=brand_name
    )
    bgt.add_task(
        email_main.send_email,
        recivers_email=[inp.email],
        subject=f"Password Reset - {brand_name}",
        body=email_content,
        is_html=True
    )

    # Update auth state
    if "provider_selection" not in state.completed_steps:
        state.completed_steps.append("provider_selection")
    state.current_step = "forgot_password"
    await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)

    return {"success": True, "message": "Password reset email sent successfully"}


@router.post("/auth/forgot-password/reset")
async def forgot_password_reset(inp: ForgotPasswordResetSchema, request: Request):
    # Validate passwords match
    if inp.new_password != inp.confirm_password:
        raise HTTPException(status_code=422, detail="Passwords do not match")

    if len(inp.new_password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    # Retrieve reset data from Redis
    reset_data = await redis_get(key=f"reset:{inp.token}")
    if not reset_data:
        raise HTTPException(status_code=404, detail="Invalid or expired reset link")

    # Clean up the reset token
    await redis_unlink(f"reset:{inp.token}")

    # Pass-through: generate redirect code with the new password
    auth_user = {
        'email': reset_data['email'],
        'name': '',
        'profile_picture': None,
        'custom_fields': {},
        'config': reset_data['config'],
        'apikey': reset_data['client_id'],
        'flow_type': 'password_reset',
        'auth_provider': 'password',
        'password': inp.new_password,
    }

    return await generate_redirect_code(
        auth_id=reset_data['request_id'],
        auth_user=auth_user,
        isfor_otp=True,
        request=request,
        return_json=True
    )
