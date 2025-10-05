from fastapi import APIRouter,Request,HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from operations.fb_operations.users_crud import check_apikey_exists,get_user_by_email
from security.unique_id import generate_unique_id
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink 
from hashlib import sha256
from exceptions.session_exp import SessionExpired
from icecream import ic
from utils.url_secret_generator import generate_url_secret,verify_url_secret

router = APIRouter(
    tags=["Authentications Access Routes"]
)

template=Jinja2Templates("templates")


class AuthSchema(BaseModel):
    apikey:str

# for getting login url
@router.post("/auth")
async def authenticate(inp:AuthSchema,request:Request):    
    configurations=check_apikey_exists(inp.apikey) # in config we got user_email, auth_methods, branding, redirect_url
    auth_id=generate_unique_id(inp.apikey)
    auth_value={'config':configurations,'apikey':inp.apikey}

    await redis_set(key=auth_id,value=auth_value,exp=540)
    return {'login_url':f"{request.base_url}auth/login/{auth_id}"} #for returning login page


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
    auth_token_payload={
        'ip':request.client.host,
        'auth_id':auth_id,
        'redirect_url': auth_values['config'].get("redirect_url",'/')
    }

    ic(auth_token_payload)
    auth_token=generate_url_secret(data=auth_token_payload)
    return template.TemplateResponse(
        name="login.html",
        context={
            'request':request,
            'scale':100,
            'is_preview':False,
            'auth_token':auth_token,
            'auth_methods':auth_values['config'].get("auth_methods",[]),
            'branding':auth_values['config'].get('branding','De-Buggers')
        }
    )



#  for getting authenticated users infos

class AuthenticatedUserSchema(BaseModel):
    code:str
    client_secret:str

@router.post('/auth/authenticated-user')
async def get_authenticated_user(inp:AuthenticatedUserSchema,request:Request):
    authenticated_user=await redis_get(key=inp.code)
    if not authenticated_user:
        raise HTTPException(
            status_code=404,
            detail="invalid code"
        )
    
    if not get_user_by_email(authenticated_user['user_email']).get('secrets',{}).get(authenticated_user['apikey'],None)==inp.client_secret:
        raise HTTPException(
            status_code=403,
            detail="invalid client secret"
        )

    if sha256(inp.client_secret.encode()).hexdigest()[:10]+authenticated_user['suffix_token']==inp.code:
        token=authenticated_user['token']
        await redis_unlink(inp.code)
        return {'token':token}