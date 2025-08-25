from fastapi import APIRouter,HTTPException,Request,Form,BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel,EmailStr
from fb_database.operations.users_crud import check_apikey_exists,check_client_secret_exists,get_user_by_id
from security.unique_id import generate_unique_id
from security.otp import generate_otp
from security.jwt_token import generate_jwt_token
from security.jwt_token import generate_jwt_token
from icecream import ic
from services.email_service import main,otp_email
import secrets
from hashlib import sha256

from globals import auth_dict,authenticated_dict


router=APIRouter(
    tags=["OTP Authentication"]
)

template=Jinja2Templates("templates")


class AuthSchema(BaseModel):
    apikey:str
    redirect_url:str

@router.post("/auth")
def authenticate(inp:AuthSchema,request:Request):
    user_id=check_apikey_exists(inp.apikey)
    if not user_id:
        raise HTTPException(
            status_code=404,
            detail="Api key doesn't exists"
        )
    
    auth_id=generate_unique_id(inp.apikey)
    auth_dict[auth_id]={'redirect_url':inp.redirect_url,'user_id':user_id}
    return f"{request.base_url}auth/login/{auth_id}" #for returning login page

@router.get("/auth/login/{auth_id}")
def login_page(auth_id:str,request:Request):
    if not auth_dict.get(auth_id,False):
        raise HTTPException(
            status_code=404,
            detail="session expired"
        )
    return template.TemplateResponse(name="login.html",context={'request':request,'auth_id':auth_id})
    

@router.post("/auth/login/otp")
def otp_page(request:Request,bgt:BackgroundTasks,email:EmailStr=Form(...),fullname:str=Form(...),auth_id:str=Form(...)):
    if not auth_dict.get(auth_id,False):
        raise HTTPException(
            status_code=404,
            detail="session expired"
        )
    
    otp=generate_otp()
    ic(otp)
    bgt.add_task(main.send_email,otp_email.generate_otp_email_content(otp=otp),email,"Otp From DeB-Authentication Service")
    extended_dict={**auth_dict[auth_id],'email':email,'full_name':fullname,'otp':otp,'verify_count':0}
    ic(extended_dict)
    auth_dict[auth_id]=extended_dict
    
    return template.TemplateResponse(name="otp.html",context={'request':request,'auth_id':auth_id}) #for returning otp page
    
    

@router.post("/auth/login/verify")
def verify_otp(auth_id:str=Form(...),otp:str=Form(...)):
    if not auth_dict.get(auth_id,False):
        raise HTTPException(
        status_code=404,
        detail="session expired"
    )

    if auth_dict[auth_id]['verify_count']==3:
        del auth_dict[auth_id]
        raise HTTPException(status_code=403,detail="max verify attempts reached")
    
    if auth_dict[auth_id]['otp']!=otp:
        ic(auth_dict[auth_id]['verify_count'])
        auth_dict[auth_id]['verify_count']+=1
        raise HTTPException(status_code=422,detail="invalid otp")
    
    temp=auth_dict[auth_id]
    ic(temp)
    del auth_dict[auth_id]
    
    suffix_token=secrets.token_urlsafe(10)
    code=sha256(get_user_by_id( temp['user_id']).get('client_secret').encode()).hexdigest()[:10]+suffix_token
    ic(code)
    authenticated_dict[code]={'token':generate_jwt_token({
            'email': temp['email'],
            'name': temp['full_name'],
            'profile_picture': None
    }),'suffix_token':suffix_token}

    return RedirectResponse(url=f"{temp['redirect_url']}?code={code}", status_code=302)
    


class AuthenticatedUserSchema(BaseModel):
    code:str
    client_secret:str

@router.post('/auth/authenticated-user')
def get_authenticated_user(inp:AuthenticatedUserSchema,request:Request):
    if not authenticated_dict.get(inp.code,0):
        raise HTTPException(
            status_code=404,
            detail="invalid code"
        )
    
    if not check_client_secret_exists(inp.client_secret):
        raise HTTPException(
            status_code=403,
            detail="invalid client secret"
        )

    if sha256(inp.client_secret.encode()).hexdigest()[:10]+authenticated_dict[inp.code]['suffix_token']==inp.code:
        return authenticated_dict[inp.code]['token']

    
        