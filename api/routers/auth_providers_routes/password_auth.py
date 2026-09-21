from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from urllib.parse import quote
from operations.redis_operations.handlers import redis_set
from utils.redirectcode_genereator import generate_redirect_code, sanitize_redirect_url
from utils.verification_service import perform_external_verification
from api.dependencies.auth_state import get_and_validate_auth_state

router = APIRouter(
    tags=["Password Authentication"]
)

class PasswordAuthSchema(BaseModel):
    request_id: str
    email: EmailStr
    password: str
    fullname: Optional[str] = ""
    custom_fields: Optional[Dict[str, Any]] = {}
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@router.post("/auth/login/password")
async def password_login(inp: PasswordAuthSchema, request: Request):
    state = await get_and_validate_auth_state(request, inp.request_id, required_step="device_validation")
    
    if "provider_selection" not in state.completed_steps:
        state.completed_steps.append("provider_selection")

    # ── Email lock enforcement ────────────────────────────────────────────────
    if state.locked_email and inp.email.lower() != state.locked_email:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Email address does not match the locked email for this session.",
                "code": "EMAIL_LOCKED"
            }
        )

    state.current_step = "authentication"

    if "authentication_started" not in state.completed_steps:
        state.completed_steps.append("authentication_started")

    redirect_urls = state.config.get('redirect_urls', {})
    is_signup = state.flow_type == 'signup'
    verification_url = (
        redirect_urls.get('signup_verification') if is_signup else redirect_urls.get('signin_verification')
    ) or redirect_urls.get('verification_url')
    failure_url = (
        redirect_urls.get('signup_failure') if is_signup else redirect_urls.get('signin_failure')
    )

    auth_data = state.auth_data or {}
    verify_count = auth_data.get('verify_count', 0)
    
    if verify_count >= 3:
        state.status = "failed"
        await redis_set(key=inp.request_id, value=state.model_dump(), exp=60)
        
        failure_redirect = None
        if failure_url:
            base_fail = sanitize_redirect_url(failure_url)
            sep = "&" if "?" in base_fail else "?"
            failure_redirect = f"{base_fail}{sep}error={quote('Maximum verification attempts reached.')}&status_code=403"
            
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Maximum verification attempts reached.",
                "status_code": 403,
                "redirect_url": failure_redirect
            }
        )

    verify_payload = {
        'request_id': inp.request_id,
        'flow_type': state.flow_type,
        'auth_provider': 'password',
        'email': inp.email,
        'password': inp.password,
        'full_name': inp.fullname,
        'custom_fields': inp.custom_fields or {},
        'latitude': inp.latitude,
        'longitude': inp.longitude,
        'ip': request.client.host if request.client else "unknown",
        'user_agent': request.headers.get("User-Agent", "unknown"),
        'client_id': state.client_id
    }

    try:
        # Call external verification endpoint if configured
        verify_result = await perform_external_verification(
            verification_url=verification_url,
            failure_url=failure_url,
            payload=verify_payload,
            request=request,
            client_id=state.client_id,
            auth_provider="password",
            identifier=inp.email,
            current_attempts=verify_count + 1,
            max_attempts=3
        )
    except HTTPException:
        # Increment failed count and persist
        auth_data['verify_count'] = verify_count + 1
        state.auth_data = auth_data
        if auth_data['verify_count'] >= 3:
            state.status = "failed"
        await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)
        raise

    # If verification returned updated name or custom fields, merge them
    if isinstance(verify_result, dict):
        if verify_result.get('custom_fields'):
            inp.custom_fields = {**(inp.custom_fields or {}), **verify_result['custom_fields']}
        if verify_result.get('full_name') or verify_result.get('name'):
            inp.fullname = verify_result.get('full_name') or verify_result.get('name')
    
    state.auth_data = {
        'email': inp.email,
        'full_name': inp.fullname,
        'custom_fields': inp.custom_fields,
        'auth_provider': 'password',
        'verify_count': 0
    }
    
    state.status = "completed"
    await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)

    auth_user = {
        'email': inp.email,
        'name': inp.fullname,
        'profile_picture': None,
        'custom_fields': inp.custom_fields,
        'config': state.config,
        'apikey': state.client_id,
        'flow_type': state.flow_type,
        'auth_provider': 'password',
        'password': inp.password
    }

    return await generate_redirect_code(
        auth_id=inp.request_id,
        auth_user=auth_user,
        isfor_otp=True,
        request=request,
        return_json=True
    )
