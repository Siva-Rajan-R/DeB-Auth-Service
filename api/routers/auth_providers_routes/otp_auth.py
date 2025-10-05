from fastapi import APIRouter,HTTPException,Request,Form,BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel,EmailStr
from operations.fb_operations.users_crud import check_apikey_exists,get_user_by_email
from security.unique_id import generate_unique_id
from security.otp import generate_otp
from exceptions.session_exp import SessionExpired
from icecream import ic
from services.email_service import main,otp_email
import secrets
from hashlib import sha256
from dotenv import load_dotenv
import os
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink,redis_curttl
from utils.redirectcode_genereator import generate_redirect_code
from utils.url_secret_generator import verify_url_secret
load_dotenv()


router=APIRouter(
    tags=["OTP Authentication"]
)

template=Jinja2Templates("templates")
    

# otp auth starts here
@router.post("/auth/login/otp")
async def otp_page(request:Request,bgt:BackgroundTasks,email:EmailStr=Form(...),fullname:str=Form(...),auth_token:str=Form(...)):
    verified_secret:dict=verify_url_secret(url_secret=auth_token,cur_ip=request.client.host) or {}
    auth_id:str=verified_secret.get('auth_id')
    auth_values=await redis_get(auth_id)

    if not auth_values:
        raise SessionExpired(redirect_url=verified_secret.get("redirect_url",'/'))
    
    otp=generate_otp()
    ic(otp)
    bgt.add_task(main.send_email,otp_email.generate_otp_email_content(otp=otp),email,"Otp From DeB-Authentication Service")
    extended_dict={**auth_values,'email':email,'full_name':fullname,'otp':otp,'verify_count':0}
    ic(extended_dict)
    ttl=await redis_curttl(auth_id)
    ic(ttl)
    await redis_set(key=auth_id,value=extended_dict,exp=ttl)
    
    return template.TemplateResponse(name="otp.html",context={'request':request,'auth_token':auth_token}) #for returning otp page
    
    

@router.post("/auth/login/verify")
async def verify_otp(request:Request,auth_token:str=Form(...),otp:str=Form(...)):
    verified_secret:dict=verify_url_secret(url_secret=auth_token,cur_ip=request.client.host) or  {}
    auth_id:str=verified_secret.get('auth_id')
    auth_values=await redis_get(key=auth_id)

    ic(auth_values)
    if not auth_values:
        raise SessionExpired(redirect_url=verified_secret.get("redirect_url",'/'))

    if auth_values['verify_count']==3:
        await redis_unlink(auth_id)
        raise HTTPException(status_code=403,detail="max verify attempts reached")
        # return template.TemplateResponse(name="otp.html",context={'request':request,'auth_token':auth_token,'error_msg':"max verify attempts reached"})
    
    if auth_values['otp']!=otp:
        ic(auth_values['verify_count'])
        auth_values['verify_count']+=1
        ttl=await redis_curttl(auth_id)
        ic(ttl)
        await redis_set(key=auth_id,value=auth_values,exp=ttl)
        raise HTTPException(status_code=422,detail="invalid otp")
        # return template.TemplateResponse(name="otp.html",context={'request':request,'auth_token':auth_token,'error_msg':"invalid otp"})

    email=auth_values['email']
    name=auth_values['full_name']
    
    ic("hello world")
    auth_values={**auth_values,'email':email,'name':name,'profile_picture':None}
    
    return await generate_redirect_code(
        auth_id=auth_id,
        auth_user=auth_values,
        isfor_otp=True
    )

# otp auth ends here  


    

    
        