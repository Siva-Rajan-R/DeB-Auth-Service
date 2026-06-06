from fastapi import APIRouter,Request,HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from operations.fb_operations.users_crud import check_apikey_exists,get_user_by_email
from core.security.unique_id import generate_unique_id
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink 
from hashlib import sha256
from exceptions.session_exp import SessionExpired
from icecream import ic 
from utils.url_secret_generator import generate_url_secret,verify_url_secret
from operations.redis_operations.session_manager import get_global_session, extend_global_session
from operations.fb_operations.end_users_crud import get_all_end_users
from utils.redirectcode_genereator import generate_redirect_code
from schemas.auth_state_schema import AuthState, DeviceFingerprint
from api.dependencies.auth_state import get_and_validate_auth_state
import time
import os
from fastapi import Depends

router = APIRouter(
    tags=["Authentications Access Routes"]
)

template=Jinja2Templates("templates")


class AuthSchema(BaseModel):
    apikey:str

@router.post("/auth")
async def authenticate(inp:AuthSchema,request:Request):    
    configurations=check_apikey_exists(inp.apikey)
    auth_id=generate_unique_id(inp.apikey)
    
    state = AuthState(
        request_id=auth_id,
        client_id=inp.apikey,
        config=configurations,
        last_activity=time.time()
    )

    await redis_set(key=auth_id,value=state.model_dump(),exp=300) # 5 minutes
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return {
        "signin_url": f"{frontend_url}/auth/request/{auth_id}/signin",
        "signup_url": f"{frontend_url}/auth/request/{auth_id}/signup"
    }


# for generating login page based on login url
@router.get("/auth/login/{auth_id}")
async def login_page(auth_id:str,request:Request):
    auth_values=await redis_get(key=auth_id)
    ic(auth_values)
    if not auth_values:
        raise HTTPException(
            status_code=404,
            detail="Auth id not found"
        )
    
    ic(request.headers.get("X-Forwarded-For"))
    
    # SSO Logic: Check for active global session
    sso_config = auth_values['config'].get('sso', {})
    if sso_config.get('enabled', False):
        global_session_id = request.cookies.get("global_session_id")
        if global_session_id:
            session = await get_global_session(global_session_id)
            if session:
                product_id = auth_values['apikey']
                users = get_all_end_users(product_id)
                user = next((u for u in users if u.id == session.user_id), None)
                if user:
                    await extend_global_session(global_session_id)
                    auth_user = {
                        'email': user.email,
                        'name': user.name,
                        'profile_picture': user.profile_picture,
                        'custom_fields': user.custom_fields
                    }
                    return await generate_redirect_code(auth_user, auth_id, isfor_otp=True, request=request)
    redirect_urls = auth_values['config'].get('redirect_urls', {})
    redirect_url = redirect_urls.get('signin_success', '/')
    
    auth_token_payload={
        'ip':request.client.host,
        'browser': request.headers.get("User-Agent"),
        'auth_id':auth_id,
        'redirect_url': redirect_url
    }

    raw_methods = auth_values['config'].get('auth_methods', [])
    enabled_methods = [m['id'] for m in raw_methods if m.get('enabled')]
    
    ic(auth_token_payload)
    auth_token=generate_url_secret(data=auth_token_payload)
    return template.TemplateResponse(
        name="login.html",
        context={
            'request':request,
            'scale':100,
            'is_preview':False,
            'auth_token':auth_token,
            'auth_methods':enabled_methods,
            'branding':auth_values['config'].get('branding','De-Buggers')
        }
    )

class InitAuthRequest(BaseModel):
    flow_type: str # 'signin' or 'signup'

@router.post("/api/auth/request/{request_id}/init")
async def init_auth_flow(
    request_id: str, 
    inp: InitAuthRequest,
    request: Request
):
    state = await get_and_validate_auth_state(request, request_id, allow_pending=True)
    # Lock the flow type and capture fingerprint
    state.flow_type = inp.flow_type
    state.status = "active"
    
    if "device_validation" not in state.completed_steps:
        state.completed_steps.append("device_validation")
        
    state.device_fingerprint = DeviceFingerprint(
        ip=request.client.host if request.client else "unknown",
        browser=request.headers.get("x-device-browser"),
        os=request.headers.get("x-device-os"),
        device=request.headers.get("x-device-type"),
        user_agent=request.headers.get("user-agent")
    )
    
    await redis_set(key=request_id, value=state.model_dump(), exp=300)

    # SSO Logic: Check for active global session
    sso_config = state.config.get('sso', {})
    if sso_config.get('enabled', False):
        global_session_id = request.cookies.get("global_session_id")
        if global_session_id:
            session = await get_global_session(global_session_id)
            if session:
                product_id = state.client_id
                users = get_all_end_users(product_id)
                user = next((u for u in users if u.id == session.user_id), None)
                if user:
                    await extend_global_session(global_session_id)
                    auth_user = {
                        'email': user.email,
                        'name': user.name,
                        'profile_picture': user.profile_picture,
                        'custom_fields': user.custom_fields,
                        'config': state.config,
                        'apikey': state.client_id
                    }
                    return await generate_redirect_code(auth_user, request_id, isfor_otp=True, request=request, return_json=True)
    
    redirect_urls = state.config.get('redirect_urls', {})
    redirect_url = redirect_urls.get('signin_success', '/')
    
    auth_token_payload={
        'ip': request.client.host,
        'browser': request.headers.get("User-Agent"),
        'auth_id': request_id,
        'redirect_url': redirect_url
    }

    raw_methods = state.config.get('auth_methods', [])
    enabled_methods = [m for m in raw_methods if m.get('enabled')]
    
    auth_token = generate_url_secret(data=auth_token_payload)
    
    # Send signup fields only if flow is signup
    signup_fields = state.config.get('signup_fields', []) if state.flow_type == 'signup' else []
    
    return {
        "auth_token": auth_token, # Used for OAuth routes
        "config": state.config,
        "enabled_methods": enabled_methods,
        "signup_fields": signup_fields,
        "branding": state.config.get('branding','De-Buggers')
    }



#  for getting authenticated users infos

class AuthenticatedUserSchema(BaseModel):
    token_id: str
    client_id: str
    client_secret: str

@router.post('/auth/authenticated-user')
async def get_authenticated_user(inp:AuthenticatedUserSchema,request:Request):
    authenticated_user=await redis_get(key=inp.token_id)
    if not authenticated_user:
        raise HTTPException(
            status_code=404,
            detail="invalid token_id"
        )
        
    if authenticated_user['apikey'] != inp.client_id:
        raise HTTPException(
            status_code=403,
            detail="invalid client id"
        )
    
    if not get_user_by_email(authenticated_user['user_email']).get('secrets',{}).get(inp.client_id,None)==inp.client_secret:
        raise HTTPException(
            status_code=403,
            detail="invalid client secret"
        )

    if sha256(inp.client_secret.encode()).hexdigest()[:10]+authenticated_user['suffix_token']==inp.token_id:
        token=authenticated_user['token']
        await redis_unlink(inp.token_id)
        return {'token':token}
        
    raise HTTPException(status_code=403, detail="invalid token_id signature")

class SignupCompleteSchema(BaseModel):
    request_id: str
    custom_fields: dict

@router.post("/api/auth/request/signup/complete")
async def signup_complete(inp: SignupCompleteSchema, request: Request):
    state = await get_and_validate_auth_state(request, inp.request_id, required_step="otp_verification")
    
    if state.flow_type != "signup" or state.current_step != "additional_fields":
        raise HTTPException(status_code=403, detail="Invalid flow state for signup complete")

    auth_data = state.auth_data
    auth_data['custom_fields'] = {**auth_data.get('custom_fields', {}), **inp.custom_fields}
    
    state.status = "completed"
    await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)

    auth_user = {
        'email': auth_data.get('email'),
        'name': auth_data.get('full_name'),
        'profile_picture': None,
        'custom_fields': auth_data['custom_fields'],
        'config': state.config,
        'apikey': state.client_id,
        'auth_provider': auth_data.get('auth_provider', 'unknown')
    }
    
    return await generate_redirect_code(
        auth_id=inp.request_id,
        auth_user=auth_user,
        isfor_otp=True,
        request=request,
        return_json=True
    )