from fastapi import APIRouter,Request,HTTPException,Depends
from api.dependencies.verify import verify_user
from fastapi.responses import RedirectResponse,Response
from security.unique_id import generate_unique_id
from security.api_key import generate_api_key
from pydantic import BaseModel,EmailStr
from input_formats.dict_inputs import User,Configuration,AuthMethods
from fb_database.operations.users_crud import create_user,get_user_by_email,get_all_users,delete_user,create_secrets,revoke_secrets,remove_apikey,update_cofigurations,get_user_secrets,check_apikey_exists
from .authentication_crud.otp_auth import authenticate,get_authenticated_user,AuthSchema,AuthenticatedUserSchema
from dotenv import load_dotenv
import os,jwt,json
from security.jwt_token import generate_jwt_token
from security.sym_encrypt import encrypt_data
from icecream import ic
from typing import List,Optional
from fastapi.templating import Jinja2Templates
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

class UpdateConfigSchema(BaseModel):
    apikey:str
    config:Configuration


DEB_USER_JWT_ALGORITHM=os.getenv("DEB_USER_JWT_ALGORITHM","HS256")
DEB_USER_JWT_KEY=os.getenv("DEB_USER_JWT_KEY")

@router.get("/user/auth")
def user_auth(request:Request):
    response=authenticate(
        inp=AuthSchema(
            apikey=os.getenv("DEB_APIKEY"),
        ),
        request=request
    )
    return response

@router.get("/user/create")
def create_users(code:str,request:Request):
    auth_user=jwt.decode(get_authenticated_user(inp=AuthenticatedUserSchema(code=code,client_secret=os.getenv("DEB_CLIENT_SECRET")),request=request)['token'],options={"verify_signature": False})

    formatted_user=User(
        name=auth_user['name'],
        email=auth_user['email'],
        secrets={},
        remove_branding=False,
        max_keys=2
    )

    create_user(formatted_user)
    json_formatted=json.dumps({'user_email':auth_user['email']})
    ic(json_formatted)
    encrypted_data=encrypt_data(json_formatted)
    ic(encrypted_data)
    token=generate_jwt_token(data={'data':encrypted_data},exp_min=15,alg=DEB_USER_JWT_ALGORITHM,key=DEB_USER_JWT_KEY)
    ic(token)
    response=RedirectResponse(url=f'http://localhost:5173/?profile={auth_user['profile_picture']}&name={auth_user['name']}',status_code=302,headers={})
    response.set_cookie(key="token",value=token,httponly=True,samesite="none",secure=True)
    return response

@router.post("/user/secrets")
def create_user_secrets(inp:Configuration,user_email:str=Depends(verify_user)):
    ic(user_email)
    user=get_user_by_email(user_email)
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="user not found"
        )
    
    no_of_secrets=len(user.get('secrets',{}))
    max_keys=user.get('max_keys')
    ic(no_of_secrets,max_keys)
    if no_of_secrets>=max_keys:
        raise HTTPException(
            status_code=403,
            detail="max keys limit reached"
        )
    
    return create_secrets(
        email=user_email,
        apikey=generate_api_key(),
        client_sceret=generate_api_key(key_prefix='DeB-Secret-',key_length=64),
        configurations=inp
    )

@router.put('/user/secrets/revoke')
def revoke_user_secrets(inp:SecretsRevokeSchema,user_email:str=Depends(verify_user)):
    return revoke_secrets(
        email=user_email,
        old_apikey=inp.apikey,
        new_apikey=generate_api_key(),
        new_client_secret=generate_api_key(key_prefix='DeB-Secret-',key_length=64)
    )

@router.delete('/user/secrets/remove')
def remove_user_apikey(apikey:str,user_email:str=Depends(verify_user)):
    ic(user_email)
    return remove_apikey(
        email=user_email,
        apikey=apikey
    )

@router.put('/user/secrets/config')
def update_apikey_configurations(inp:UpdateConfigSchema,user_email:str=Depends(verify_user)):

    if len(inp.config.get("auth_methods"))<=0:
        raise HTTPException(
            status_code=422,
            detail="Choose atleast one auth method"
        )

    return update_cofigurations(email=user_email,apikey=inp.apikey,new_configurations=inp.config)


@router.get("/user/secrets")
def get_user_by_pk(user_email:str=Depends(verify_user)):
    ic(user_email)
    user=get_user_secrets(user_email=user_email)
    return user

@router.get("/users")
def get_users():
    if os.getenv('CURRENT_ENVIRONMENT')!='development':
        raise HTTPException(
            status_code=404,
            detail='not found'
        )
    return get_all_users()

@router.delete("/users")
def delete_users(user_email:EmailStr):
    return delete_user(user_email=user_email)

@router.delete("/user/logout")
def logout(response:Response):
    response.delete_cookie(key="token",httponly=True,samesite="none",secure=True)
    return {"message": "Logged out successfully"}

@router.get('/user/auth/preview')
def get_user_login_page(apikey:str,request:Request):
    config=check_apikey_exists(apikey=apikey)
    if not config:
        raise HTTPException(
            status_code=404,
            detail="apikey not found"
        )
    
    return template.TemplateResponse(name="login.html",context={'request':request,'is_preview':True,'scale':50,'auth_id':None,'auth_methods':config.get('auth_methods',[]),"branding":config.get('branding',"De-Buggers")})