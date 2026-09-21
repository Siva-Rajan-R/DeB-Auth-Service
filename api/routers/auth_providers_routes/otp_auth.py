from fastapi import APIRouter,HTTPException,Request,BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel,EmailStr
from typing import Optional
from operations.mongo_operations.users_crud import check_apikey_exists,get_user_by_email
from core.security.unique_id import generate_unique_id
from core.security.otp import generate_otp
from exceptions.session_exp import SessionExpired
from icecream import ic
from services.email_service import main,otp_email
from services.msg91_service import msg91_service
import secrets
from hashlib import sha256
from dotenv import load_dotenv
import os
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink,redis_curttl
from utils.redirectcode_genereator import generate_redirect_code
from utils.verification_service import perform_external_verification
from utils.url_secret_generator import verify_url_secret
from api.dependencies.auth_state import get_and_validate_auth_state
from operations.mongo_operations.analytics_crud import log_sms_otp_dispatch, log_audit_event
load_dotenv()


router=APIRouter(
    tags=["OTP Authentication"]
)

class OtpSendSchema(BaseModel):
    request_id: str
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    fullname: str = ""
    custom_fields: dict = {}

class OtpVerifySchema(BaseModel):
    request_id: str
    otp: str

# otp auth starts here
@router.post("/auth/login/otp")
async def otp_page(inp: OtpSendSchema, request:Request, bgt:BackgroundTasks):
    state = await get_and_validate_auth_state(request, inp.request_id, required_step="device_validation")
    
    if "provider_selection" not in state.completed_steps:
        state.completed_steps.append("provider_selection")
        
    if not inp.email and not inp.mobile_number:
        raise HTTPException(
            status_code=422,
            detail="Either email or mobile number must be provided."
        )

    fullname = inp.fullname
    custom_fields = inp.custom_fields

    if inp.mobile_number:
        mobile_number = inp.mobile_number.strip()
        
        # ── Phone lock enforcement ────────────────────────────────────────────────
        if getattr(state, 'locked_phone', None) and mobile_number != state.locked_phone:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Phone number does not match the locked phone number for this session.",
                    "code": "PHONE_LOCKED"
                }
            )
            
        try:
            verification_id = await msg91_service.send_otp(mobile_number=mobile_number)
            if not verification_id:
                raise Exception("Did not receive verificationId from MSG91.")
        except Exception as e:
            ic(f"Error sending mobile OTP: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to send OTP to mobile number."
            )
            
        # Log SMS OTP dispatch asynchronously
        bgt.add_task(log_sms_otp_dispatch, state.client_id)
        bgt.add_task(log_audit_event, state.client_id, request.client.host if request.client else "unknown", "otp-phone", mobile_number, "OTP_REQUEST", "Ongoing")
            
        # Use a dummy email for systems expecting email uniqueness / presence
        email = inp.email or ""
        
        state.auth_data = {
            'email': email,
            'mobile_number': mobile_number,
            'verification_id': verification_id,
            'full_name': fullname,
            'verify_count': 0,
            'custom_fields': custom_fields,
            'auth_provider': 'otp-phone'
        }
    else:
        email = inp.email
        # ── Email lock enforcement ────────────────────────────────────────────────
        if state.locked_email and email.lower() != state.locked_email:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Email address does not match the locked email for this session.",
                    "code": "EMAIL_LOCKED"
                }
            )

        otp=generate_otp()
        ic(otp)
        email_content=otp_email.generate_otp_email_content(otp=otp)
        bgt.add_task(main.send_email,recivers_email=[email],subject="Otp From DeB-Authentication Service",body=email_content,is_html=True)
        bgt.add_task(log_audit_event, state.client_id, request.client.host if request.client else "unknown", "otp-email", email, "OTP_REQUEST", "Ongoing")
        
        state.auth_data = {
            'email': email,
            'full_name': fullname,
            'otp': otp,
            'verify_count': 0,
            'custom_fields': custom_fields,
            'auth_provider': 'otp-email'
        }
    
    state.current_step = "authentication"
    if "authentication_started" not in state.completed_steps:
        state.completed_steps.append("authentication_started")
        
    await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)
    
    return {"success": True, "message": "OTP sent successfully"}
    
    

@router.post("/auth/login/verify")
async def verify_otp(inp: OtpVerifySchema, request:Request):
    state = await get_and_validate_auth_state(request, inp.request_id, required_step="authentication_started")
    otp = inp.otp
    
    auth_data = state.auth_data

    if auth_data.get('verify_count', 0) >= 3:
        state.status = "failed"
        await redis_set(key=inp.request_id, value=state.model_dump(), exp=60)
        
        # Log failure
        import asyncio
        asyncio.create_task(log_audit_event(state.client_id, request.client.host if request.client else "unknown", auth_data.get('auth_provider', 'otp'), auth_data.get('mobile_number') or auth_data.get('email'), "LOGIN_FAILED", "FAILED"))
        
        redirect_urls = state.config.get('redirect_urls', {})
        failure_url = redirect_urls.get('signup_failure') if state.flow_type == 'signup' else redirect_urls.get('signin_failure')
        
        if failure_url:
            raise HTTPException(status_code=403, detail={"message": "max verify attempts reached", "redirect_url": failure_url})
        else:
            raise HTTPException(status_code=403, detail="max verify attempts reached")
    
    verification_id = auth_data.get('verification_id')
    if verification_id:
        # MSG91 OTP Verification
        try:
            is_valid = await msg91_service.verify_otp(verification_id=verification_id, code=otp, mobile_number=auth_data.get('mobile_number'))
            if not is_valid:
                raise Exception("MSG91 validation failed")
        except Exception as e:
            ic(f"Mobile OTP verification failed: {e}")
            auth_data['verify_count'] = auth_data.get('verify_count', 0) + 1
            state.auth_data = auth_data
            await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)
            
            import asyncio
            asyncio.create_task(log_audit_event(state.client_id, request.client.host if request.client else "unknown", auth_data.get('auth_provider', 'otp'), auth_data.get('mobile_number') or auth_data.get('email'), "LOGIN_FAILED", "FAILED"))
            raise HTTPException(status_code=422, detail="invalid otp")
    else:
        # Local email OTP verification
        if auth_data.get('otp') != otp:
            auth_data['verify_count'] = auth_data.get('verify_count', 0) + 1
            state.auth_data = auth_data
            await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)
            
            import asyncio
            asyncio.create_task(log_audit_event(state.client_id, request.client.host if request.client else "unknown", auth_data.get('auth_provider', 'otp'), auth_data.get('mobile_number') or auth_data.get('email'), "LOGIN_FAILED", "FAILED"))
            raise HTTPException(status_code=422, detail="invalid otp")

    # OTP Verified Successfully
    if "otp_verification" not in state.completed_steps:
        state.completed_steps.append("otp_verification")

    if state.flow_type == "signup" and state.config.get("signup_fields"):
        state.current_step = "additional_fields"
        await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)
        return {"success": True, "next_step": "additional_fields"}
    
    redirect_urls = state.config.get('redirect_urls', {})
    is_signup = state.flow_type == 'signup'
    verification_url = (
        redirect_urls.get('signup_verification') if is_signup else redirect_urls.get('signin_verification')
    ) or redirect_urls.get('verification_url')
    failure_url = (
        redirect_urls.get('signup_failure') if is_signup else redirect_urls.get('signin_failure')
    )

    verify_payload = {
        'request_id': inp.request_id,
        'flow_type': state.flow_type,
        'auth_provider': auth_data.get('auth_provider', 'otp'),
        'email': auth_data.get('email'),
        'mobile_number': auth_data.get('mobile_number'),
        'full_name': auth_data.get('full_name'),
        'custom_fields': auth_data.get('custom_fields', {}),
        'ip': request.client.host if request.client else "unknown",
        'user_agent': request.headers.get("User-Agent", "unknown"),
        'client_id': state.client_id
    }

    # Call external verification endpoint if configured
    verify_result = await perform_external_verification(
        verification_url=verification_url,
        failure_url=failure_url,
        payload=verify_payload,
        request=request,
        client_id=state.client_id,
        auth_provider=auth_data.get('auth_provider', 'otp'),
        identifier=auth_data.get('email') or auth_data.get('mobile_number') or "unknown"
    )

    if isinstance(verify_result, dict):
        if verify_result.get('custom_fields'):
            auth_data['custom_fields'] = {**(auth_data.get('custom_fields') or {}), **verify_result['custom_fields']}
        if verify_result.get('full_name') or verify_result.get('name'):
            auth_data['full_name'] = verify_result.get('full_name') or verify_result.get('name')

    # Otherwise finish auth
    state.status = "completed"
    await redis_set(key=inp.request_id, value=state.model_dump(), exp=300)

    auth_user = {
        'email': auth_data['email'],
        'mobile_number': auth_data.get('mobile_number'),
        'name': auth_data['full_name'],
        'profile_picture': None,
        'custom_fields': auth_data.get('custom_fields', {}),
        'config': state.config,
        'apikey': state.client_id,
        'flow_type': state.flow_type,
        'auth_provider': auth_data.get('auth_provider', 'otp')
    }
    
    return await generate_redirect_code(
        auth_id=inp.request_id,
        auth_user=auth_user,
        isfor_otp=True,
        request=request,
        return_json=True
    )

# otp auth ends here  


    

    
        