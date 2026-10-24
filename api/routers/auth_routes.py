from fastapi import APIRouter,Request,HTTPException,BackgroundTasks
from typing import Optional, Dict, Any
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from operations.mongo_operations.users_crud import check_apikey_exists,get_user_by_email
from core.security.unique_id import generate_unique_id
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink 
from hashlib import sha256
from exceptions.session_exp import SessionExpired
from icecream import ic 
from utils.url_secret_generator import generate_url_secret,verify_url_secret
from operations.redis_operations.session_manager import get_global_session, extend_global_session
from operations.mongo_operations.end_users_crud import get_all_end_users, update_end_user
from utils.redirectcode_genereator import generate_redirect_code
from utils.verification_service import perform_external_verification
from operations.mongo_operations.analytics_crud import log_auth_request

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
    apikey: str
    flow_type: Optional[str] = "signin"
    verify_url: Optional[str] = None
    verification_url: Optional[str] = None
    redirect_url: Optional[str] = None
    signin_verification: Optional[str] = None
    signup_verification: Optional[str] = None
    signin_redirect: Optional[str] = None
    signup_redirect: Optional[str] = None
    additional_infos: Optional[Dict[str, Any]] = None

@router.post("/auth")
async def authenticate(inp: AuthSchema, request: Request, bgt: BackgroundTasks = None):    
    configurations = await check_apikey_exists(inp.apikey)
    auth_id = generate_unique_id(inp.apikey)
    
    # Merge dynamically passed verification and redirect URLs into configurations['redirect_urls']
    redirect_urls = dict(configurations.get('redirect_urls') or {})
    add_infos = inp.additional_infos or {}

    dyn_verify = (
        inp.verify_url 
        or inp.verification_url 
        or add_infos.get('verify_url') 
        or add_infos.get('verification_url')
    )
    dyn_redirect = (
        inp.redirect_url 
        or add_infos.get('redirect_url')
    )
    dyn_signin_verify = (
        inp.signin_verification 
        or add_infos.get('signin_verification') 
        or (dyn_verify if inp.flow_type != 'signup' else None)
    )
    dyn_signup_verify = (
        inp.signup_verification 
        or add_infos.get('signup_verification') 
        or (dyn_verify if inp.flow_type == 'signup' else None)
    )
    dyn_signin_redirect = (
        inp.signin_redirect 
        or add_infos.get('signin_redirect') 
        or (dyn_redirect if inp.flow_type != 'signup' else None)
    )
    dyn_signup_redirect = (
        inp.signup_redirect 
        or add_infos.get('signup_redirect') 
        or (dyn_redirect if inp.flow_type == 'signup' else None)
    )

    if dyn_verify:
        redirect_urls['verification_url'] = dyn_verify
    if dyn_signin_verify:
        redirect_urls['signin_verification'] = dyn_signin_verify
    if dyn_signup_verify:
        redirect_urls['signup_verification'] = dyn_signup_verify
    if dyn_signin_redirect:
        redirect_urls['signin_success'] = dyn_signin_redirect
    if dyn_signup_redirect:
        redirect_urls['signup_success'] = dyn_signup_redirect

    configurations['redirect_urls'] = redirect_urls

    state = AuthState(
        request_id=auth_id,
        client_id=inp.apikey,
        config=configurations,
        flow_type=inp.flow_type or "signin",
        last_activity=time.time(),
        additional_infos=inp.additional_infos
    )

    await redis_set(key=auth_id, value=state.model_dump(), exp=300) # 5 minutes
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return {
        "signin_url": f"{frontend_url}/auth/request/{auth_id}/signin",
        "signup_url": f"{frontend_url}/auth/request/{auth_id}/signup"
    }


@router.get("/auth/login/{auth_id}")
async def login_page(auth_id:str,request:Request, bgt: BackgroundTasks):
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
                users = await get_all_end_users(product_id)
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
    flow_type: str                        # 'signin' or 'signup'
    prefill_email: str = ""              # Optional: lock this email for the whole session
    prefill_phone: str = ""              # Optional: lock this phone for the whole session
    lock_method: str = ""                # Optional: lock method used
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
    
    if state.config.get('location_based_auth'):
        if inp.latitude is None or inp.longitude is None:
            raise HTTPException(status_code=403, detail="Location permissions are required for authentication in this app.")
        state.latitude = inp.latitude
        state.longitude = inp.longitude
    
    if "device_validation" not in state.completed_steps:
        state.completed_steps.append("device_validation")
        
    state.device_fingerprint = DeviceFingerprint(
        ip=request.client.host if request.client else "unknown",
        browser=request.headers.get("x-device-browser"),
        os=request.headers.get("x-device-os"),
        device=request.headers.get("x-device-type"),
        user_agent=request.headers.get("user-agent")
    )
    
    flow = state.flow_type if state.flow_type in ['signin', 'signup'] else 'signin'
    flow_specific = state.config.get(flow) if isinstance(state.config.get(flow), dict) else {}

    raw_methods = flow_specific.get('auth_methods') if (flow_specific.get('auth_methods') is not None) else state.config.get('auth_methods', [])
    email_otp_enabled = any((m['id'] == 'email_otp' or m['id'] == 'otp') and m.get('enabled') for m in raw_methods)
    mobile_otp_enabled = any(m['id'] == 'mobile_otp' and m.get('enabled') for m in raw_methods)

    # Store locked email in state if provided and email OTP is enabled
    if inp.prefill_email and email_otp_enabled:
        state.locked_email = inp.prefill_email.strip().lower()
    # Store locked phone in state if provided and mobile OTP is enabled
    if inp.prefill_phone and mobile_otp_enabled:
        state.locked_phone = inp.prefill_phone.strip()
    
    # Store lock method if provided
    if inp.lock_method:
        state.lock_method = inp.lock_method.strip()

    await redis_set(key=request_id, value=state.model_dump(), exp=300)

    # SSO Logic: Check for active global session
    sso_config = state.config.get('sso', {})
    if sso_config.get('enabled', False):
        # 1. Domain Validation: match caller's Origin or Referer against registered SSO domains
        client_origin = request.headers.get("origin") or request.headers.get("referer") or ""
        # Extract host name
        from urllib.parse import urlparse
        parsed = urlparse(client_origin)
        caller_host = parsed.netloc.lower() or parsed.path.lower()
        if ":" in caller_host:
            caller_host = caller_host.split(":")[0]

        # Verify host matches any registered domains with wildcards (*.domain.com, *domain*, etc.)
        matched_domain = False
        registered_domains = sso_config.get('domains', [])
        for domain in registered_domains:
            # normalize domain from db object or string
            d_str = (domain.get("domain") if isinstance(domain, dict) else str(domain)).strip().lower()
            if not d_str:
                continue
            
            # Match rules:
            # a) Exact match
            if caller_host == d_str:
                matched_domain = True
                break
            # b) *.domain.com wildcard
            if d_str.startswith("*."):
                suffix = d_str[2:]
                if caller_host.endswith(suffix):
                    matched_domain = True
                    break
            # c) *domain* format
            if d_str.startswith("*") and d_str.endswith("*"):
                pattern = d_str[1:-1]
                if pattern in caller_host:
                    matched_domain = True
                    break
            # d) *domain format
            elif d_str.startswith("*"):
                pattern = d_str[1:]
                if caller_host.endswith(pattern):
                    matched_domain = True
                    break
            # e) domain* format
            elif d_str.endswith("*"):
                pattern = d_str[:-1]
                if caller_host.startswith(pattern):
                    matched_domain = True
                    break

        if matched_domain:
            global_session_id = request.cookies.get("global_session_id")
            if global_session_id:
                session = await get_global_session(global_session_id)
                if session:
                    # 2. Browser Signature Match validation (Security confirmation)
                    cur_browser = request.headers.get("User-Agent", "unknown")
                    if session.device_info == cur_browser:
                        product_id = state.client_id
                        users = await get_all_end_users(product_id)
                        user = next((u for u in users if u.email == session.user_id or u.id == session.user_id), None)
                        if user:
                            await extend_global_session(global_session_id)
                            # Record this login site in user's custom fields/history
                            if 'signed_in_sites' not in user.custom_fields:
                                user.custom_fields['signed_in_sites'] = []
                            site_info = {"url": client_origin or caller_host, "timestamp": time.time()}
                            if site_info["url"] not in [s.get("url") for s in user.custom_fields['signed_in_sites'] if isinstance(s, dict)]:
                                user.custom_fields['signed_in_sites'].append(site_info)
                            await update_end_user(product_id, user)

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
    if flow == 'signup':
        redirect_url = redirect_urls.get('signup_success') or redirect_urls.get('signin_success', '/')
    else:
        redirect_url = redirect_urls.get('signin_success', '/')
    
    auth_token_payload={
        'ip': request.client.host,
        'browser': request.headers.get("User-Agent"),
        'auth_id': request_id,
        'redirect_url': redirect_url
    }

    enabled_methods = [m for m in raw_methods if m.get('enabled')]
    
    auth_token = generate_url_secret(data=auth_token_payload)
    
    # Send signup fields only if flow is signup
    signup_fields = state.config.get('signup_fields', []) if state.flow_type == 'signup' else []

    flow_ui = {**state.config.get('ui', {}), **(flow_specific.get('ui') or {})} if isinstance(flow_specific.get('ui'), dict) else state.config.get('ui', {})

    active_config = {
        **state.config,
        "ui": flow_ui,
        "auth_methods": raw_methods,
    }
    
    return {
        "auth_token": auth_token, # Used for OAuth routes
        "config": active_config,
        "enabled_methods": enabled_methods,
        "signup_fields": signup_fields,
        "branding": active_config.get('branding', 'De-Buggers')
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
    
    user_data = await get_user_by_email(authenticated_user['user_email'])
    if not user_data or user_data.get('secrets',{}).get(inp.client_id,None)!=inp.client_secret:
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
    merged_custom_fields = {**auth_data.get('custom_fields', {}), **inp.custom_fields}
    auth_data['custom_fields'] = merged_custom_fields

    redirect_urls = state.config.get('redirect_urls', {})
    add_infos = state.additional_infos or {}
    verification_url = (
        redirect_urls.get('signup_verification') 
        or redirect_urls.get('verification_url')
        or add_infos.get('signup_verification')
        or add_infos.get('verify_url')
        or add_infos.get('verification_url')
    )
    failure_url = (
        redirect_urls.get('signup_failure')
        or add_infos.get('signup_failure')
        or add_infos.get('failure_url')
    )

    verify_payload = {
        'request_id': inp.request_id,
        'flow_type': 'signup',
        'auth_provider': auth_data.get('auth_provider', 'signup'),
        'email': auth_data.get('email'),
        'mobile_number': auth_data.get('mobile_number'),
        'full_name': auth_data.get('full_name'),
        'custom_fields': merged_custom_fields,
        'ip': request.client.host if request.client else "unknown",
        'user_agent': request.headers.get("User-Agent", "unknown"),
        'client_id': state.client_id
    }

    verify_result = await perform_external_verification(
        verification_url=verification_url,
        failure_url=failure_url,
        payload=verify_payload,
        request=request,
        client_id=state.client_id,
        auth_provider=auth_data.get('auth_provider', 'signup'),
        identifier=auth_data.get('email') or auth_data.get('mobile_number') or "unknown"
    )

    if isinstance(verify_result, dict):
        if verify_result.get('custom_fields'):
            auth_data['custom_fields'] = {**auth_data['custom_fields'], **verify_result['custom_fields']}
        if verify_result.get('full_name') or verify_result.get('name'):
            auth_data['full_name'] = verify_result.get('full_name') or verify_result.get('name')
    
    state.status = "completed"
    await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)

    auth_user = {
        'email': auth_data.get('email'),
        'name': auth_data.get('full_name'),
        'profile_picture': None,
        'custom_fields': auth_data['custom_fields'],
        'config': state.config,
        'apikey': state.client_id,
        'flow_type': 'signup',
        'auth_provider': auth_data.get('auth_provider', 'signup')
    }
    
    return await generate_redirect_code(
        auth_id=inp.request_id,
        auth_user=auth_user,
        isfor_otp=True,
        request=request,
        return_json=True
    )