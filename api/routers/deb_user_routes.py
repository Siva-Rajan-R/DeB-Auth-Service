from fastapi import APIRouter,Request,HTTPException,Depends,BackgroundTasks
from api.dependencies.token_verification import verify_user
from api.dependencies.token_revocation import revoke_user
from fastapi.responses import RedirectResponse,Response
from core.security.unique_id import generate_unique_id
from core.security.api_key import generate_api_key
from pydantic import BaseModel,EmailStr
from input_formats.dict_inputs import User,Configuration,AuthMethods
from operations.mongo_operations.users_crud import create_user,get_user_by_email,get_all_users,delete_user,create_secrets,revoke_secrets,regenerate_client_secret,remove_apikey,update_cofigurations,get_user_secrets,check_apikey_exists,update_user_profile
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink
from core.security.otp import generate_otp
from services.email_service.main import send_email
from .auth_routes import authenticate,get_authenticated_user,AuthSchema,AuthenticatedUserSchema
from dotenv import load_dotenv
import os,jwt,json
from core.security.jwt_token import generate_jwt_token
from core.security.sym_encrypt import encrypt_data
from icecream import ic
from typing import List,Optional
from fastapi.templating import Jinja2Templates
from exceptions.session_exp import SessionExpired
load_dotenv()

router=APIRouter(
    tags=["User CRUD"]
)


template=Jinja2Templates("templates")
class UserSchema(BaseModel):
    name:str
    email:EmailStr

class UserDeleteSchema(BaseModel):
    user_id:str

class SecretsRevokeSchema(BaseModel):
    apikey:str

class ClientSecretRegenerateSchema(BaseModel):
    apikey:str

class UpdateConfigSchema(BaseModel):
    apikey:str
    config:Configuration


DEB_USER_JWT_ALGORITHM=os.getenv("DEB_USER_JWT_ALGORITHM","HS256")
DEB_USER_JWT_KEY=os.getenv("DEB_USER_JWT_KEY")
DEB_USER_REFRESH_JWT_ALGORITHM=os.getenv("DEB_USER_REFRESH_JWT_ALGORITHM")
DEB_USER_REFRESH_KEY=os.getenv("DEB_USER_REFRESH_KEY")

@router.get("/user/auth")
async def user_auth(request:Request):
    response=await authenticate(
        inp=AuthSchema(
            apikey=os.getenv("DEB_APIKEY", ""),
        ),
        request=request
    )
    return response

@router.get("/user/create")
async def create_users(request:Request,res:Response,token_id:Optional[str]=None):
    ic(token_id)
    FRONTEND_URL=os.getenv("FRONTEND_URL")
    if not token_id:
        raise SessionExpired(
            redirect_url=FRONTEND_URL,
            message="Authentication Falied redirecting to DeB-Auth-Service"
        )
    
    token=await get_authenticated_user(inp=AuthenticatedUserSchema(token_id=token_id,client_id=os.getenv("DEB_APIKEY", ""),client_secret=os.getenv("DEB_CLIENT_SECRET", "")),request=request)
    ic(token)
    if not token.get('token',None):
        raise HTTPException(
            status_code=404,
            detail="token is missing from DeB-Auth-Service"
        )
    
    auth_user=jwt.decode(token['token'],options={"verify_signature": False})
    user_email = auth_user.get('email', '')
    raw_name = auth_user.get('name')
    if not raw_name or str(raw_name).strip() in ['', 'None', 'null', 'undefined']:
        user_name = user_email.split('@')[0] if user_email and '@' in user_email else ''
    else:
        user_name = raw_name

    profile_pic = auth_user.get('profile_picture') or ''

    formatted_user=User(
        name=user_name,
        email=user_email,
        secrets={},
        remove_branding=False,
        max_keys=2
    )

    await create_user(formatted_user)
    json_formatted=json.dumps({'user_email':user_email})
    ic(json_formatted)
    encrypted_data=encrypt_data(json_formatted)
    ic(encrypted_data)
    access_token=generate_jwt_token(data={'data':encrypted_data},exp_min=15,alg=DEB_USER_JWT_ALGORITHM,key=DEB_USER_JWT_KEY)
    refresh_token=generate_jwt_token(data={'data':encrypted_data},exp_days=5,alg=DEB_USER_REFRESH_JWT_ALGORITHM,key=DEB_USER_REFRESH_KEY)
    ic(token)
    
    response=RedirectResponse(url=f'{FRONTEND_URL}?profile={profile_pic}&name={user_name}&email={user_email}&access_token={access_token}&refresh_token={refresh_token}',status_code=302)
    # response.set_cookie(key="token",value=token,httponly=True,samesite='none',secure=True)
    ic(response.headers,response.__dict__)
    # return {"redirect_url":f'{FRONTEND_URL}?profile={profile_pic}&name={user_name}'}
    return response

@router.post("/user/secrets")
async def create_user_secrets(inp:Configuration,user_email:str=Depends(verify_user)):
    ic(user_email)

    
    return await create_secrets(
        email=user_email,
        apikey=generate_api_key(),
        client_secret=generate_api_key(key_prefix='DAuth-Secret-',key_length=64),
        configurations=inp
    )

@router.put('/user/secrets/revoke')
async def revoke_user_secrets(inp:SecretsRevokeSchema,user_email:str=Depends(verify_user)):
    return await revoke_secrets(
        email=user_email,
        old_apikey=inp.apikey,
        new_apikey=generate_api_key(),
        new_client_secret=generate_api_key(key_prefix='DAuth-Secret-',key_length=64)
    )

@router.put('/user/secrets/regenerate_client_secret')
async def regenerate_user_client_secret(inp:ClientSecretRegenerateSchema,user_email:str=Depends(verify_user)):
    return await regenerate_client_secret(
        email=user_email,
        apikey=inp.apikey,
        new_client_secret=generate_api_key(key_prefix='DAuth-Secret-',key_length=64)
    )

@router.delete('/user/secrets/remove')
async def remove_user_apikey(apikey:str,user_email:str=Depends(verify_user)):
    ic(user_email)
    return await remove_apikey(
        email=user_email,
        apikey=apikey
    )

async def revoke_active_sessions_for_apikey(apikey: str):
    try:
        from configs.redis_config import redis
        import json
        async for key in redis.scan_iter("*"):
            data = await redis.get(key)
            if data:
                try:
                    val = json.loads(data)
                    if isinstance(val, dict) and val.get("client_id") == apikey:
                        val["status"] = "revoked"
                        await redis.set(name=key, value=json.dumps(val), ex=300)
                except Exception:
                    pass
    except Exception as e:
        ic(f"Error revoking active sessions: {e}")

@router.put('/user/secrets/config')
async def update_apikey_configurations(inp:UpdateConfigSchema,user_email:str=Depends(verify_user)):

    enabled_methods = [m for m in inp.config.get("auth_methods", []) if m.get("enabled")]
    if len(enabled_methods)<=0:
        raise HTTPException(
            status_code=422,
            detail="Choose atleast one auth method"
        )

    res = await update_cofigurations(email=user_email,apikey=inp.apikey,new_configurations=inp.config)
    await revoke_active_sessions_for_apikey(inp.apikey)
    return res

from fastapi import UploadFile, File, Form
from typing import Optional
from services.minio_storage import upload_logo_to_minio, delete_logo_from_minio
import time

@router.post('/user/secrets/upload-logo')
async def upload_logo(
    file: UploadFile = File(...),
    old_logo_url: Optional[str] = Form(None),
    user_email: str = Depends(verify_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image file uploads are supported.")
    try:
        if old_logo_url:
            delete_logo_from_minio(old_logo_url)
            
        file_bytes = await file.read()
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "png"
        unique_filename = f"logo_{int(time.time())}.{file_extension}"
        public_url = upload_logo_to_minio(
            file_data=file_bytes,
            file_name=unique_filename,
            content_type=file.content_type
        )
        return {"success": True, "logo_url": public_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/secrets")
async def get_user_by_pk(request:Request,user_email:str=Depends(verify_user)):

    ic(user_email,request.cookies,request.cookies.get("token"))
    user=await get_user_secrets(user_email=user_email)
    return user

@router.get("/users")
async def get_users():
    if os.getenv('CURRENT_ENVIRONMENT')!='development':
        raise HTTPException(
            status_code=404,
            detail='not found'
        )
    return await get_all_users()

@router.delete("/user")
async def delete_users(user_email:EmailStr):
    return await delete_user(user_email=user_email)

@router.delete("/user/logout")
def logout(response:Response,req:Request):
    ic(req.cookies.get("token"))
    response.delete_cookie(key="token",httponly=True,samesite="none",secure=True)
    return {"message": "Logged out successfully"}

@router.get('/user/auth/preview')
async def get_user_login_page(apikey:str,request:Request):
    config=await check_apikey_exists(apikey=apikey)
    if not config:
        raise HTTPException(
            status_code=404,
            detail="apikey not found"
        )
    
    return template.TemplateResponse(
        name="login.html",
        context={
            'request':request,
            'is_preview':True,
            'scale':50,
            'auth_id':None,
            'auth_methods':config.get('auth_methods',[]),
            "branding":config.get('branding',"De-Buggers")
        }
    )

@router.get("/user/token")
def get_new_token(req:Request,new_token:bool=Depends(revoke_user)):
    ic(new_token)
    return {
        'access_token':new_token
    }

class ProfileUpdateSchema(BaseModel):
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None

@router.get("/user/profile")
async def get_profile(user_email: str = Depends(verify_user)):
    user = await get_user_by_email(user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "billing_name": user.get("billing_name", ""),
        "billing_address": user.get("billing_address", "")
    }

@router.post("/user/profile/update")
async def update_profile(inp: ProfileUpdateSchema, user_email: str = Depends(verify_user)):
    update_data = {}
    if inp.billing_name is not None:
        update_data["billing_name"] = inp.billing_name
    if inp.billing_address is not None:
        update_data["billing_address"] = inp.billing_address
        
    if update_data:
        await update_user_profile(user_email, update_data)
        
    return {"message": "Profile updated successfully"}

class DeleteReasonSchema(BaseModel):
    reason: str

@router.post("/user/delete/request-otp")
async def request_delete_otp(inp: DeleteReasonSchema, background_tasks: BackgroundTasks, user_email: str = Depends(verify_user)):
    otp = generate_otp(6)
    
    # Store OTP and reason in Redis with 5 min expiry
    await redis_set(f"delete_otp_{user_email}", otp, 300)
    await redis_set(f"delete_reason_{user_email}", inp.reason, 300)
    
    html_body = f"""
    <div style="font-family: 'Inter', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
        <div style="background-color: #fef2f2; padding: 32px 24px; border-bottom: 1px solid #fee2e2; text-align: center;">
            <h2 style="margin: 0; color: #dc2626; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Action Required</h2>
            <p style="margin: 8px 0 0; color: #991b1b; font-size: 15px;">Account Deletion Request</p>
        </div>
        <div style="padding: 32px 24px;">
            <p style="margin: 0 0 16px; color: #334155; font-size: 16px; line-height: 24px;">Hello,</p>
            <p style="margin: 0 0 24px; color: #475569; font-size: 15px; line-height: 24px;">We received a request to permanently delete your DAuth account. Please use the verification code below to confirm this action.</p>
            
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
                <span style="display: block; font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Verification Code</span>
                <span style="display: block; font-family: monospace; font-size: 36px; font-weight: 700; color: #0f172a; letter-spacing: 8px;">{otp}</span>
            </div>
            
            <div style="background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 4px; margin-bottom: 24px;">
                <p style="margin: 0; color: #b45309; font-size: 14px; font-weight: 500;">⏱️ This code will expire in <strong>5 minutes</strong>.</p>
            </div>
            
            <p style="margin: 0 0 24px; color: #475569; font-size: 14px; line-height: 22px;">If you did not request to delete your account, please ignore this email and immediately change your password to secure your account.</p>
        </div>
        <div style="background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
            <p style="margin: 0; color: #64748b; font-size: 13px;">Need help? Reply to this email to contact support.</p>
            <p style="margin: 8px 0 0; color: #94a3b8; font-size: 12px;">&copy; DAuth Security Team</p>
        </div>
    </div>
    """
    background_tasks.add_task(send_email, [user_email], "DAuth - Account Deletion Verification", html_body, True)
    
    return {"message": "OTP sent to email"}

class DeleteVerifySchema(BaseModel):
    otp: str

@router.post("/user/delete/verify")
async def verify_delete_otp(inp: DeleteVerifySchema, user_email: str = Depends(verify_user)):
    stored_otp = await redis_get(f"delete_otp_{user_email}")
    if not stored_otp or stored_otp != inp.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    reason = await redis_get(f"delete_reason_{user_email}")
    
    # Process account deletion
    user = await get_user_by_email(user_email)
    if user:
        await delete_user(user["_id"])
    
    # Cleanup redis
    await redis_unlink(f"delete_otp_{user_email}")
    await redis_unlink(f"delete_reason_{user_email}")
    
    return {"message": "Account successfully deleted. We are sorry to see you go."}
