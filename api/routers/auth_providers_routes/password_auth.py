from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from operations.redis_operations.handlers import redis_set
from utils.redirectcode_genereator import generate_redirect_code
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

@router.post("/auth/login/password")
async def password_login(inp: PasswordAuthSchema, request: Request):
    state = await get_and_validate_auth_state(request, inp.request_id, required_step="device_validation")
    
    if "provider_selection" not in state.completed_steps:
        state.completed_steps.append("provider_selection")
        
    state.current_step = "authentication"
    if "authentication_started" not in state.completed_steps:
        state.completed_steps.append("authentication_started")

    # In Pass-Through Authentication, the password is encrypted inside the token
    # and sent to the client backend for verification.
    
    state.auth_data = {
        'email': inp.email,
        'full_name': inp.fullname,
        'custom_fields': inp.custom_fields,
        'auth_provider': 'password'
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
