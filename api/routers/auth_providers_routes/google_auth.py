from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import RedirectResponse
from operations.fb_operations.users_crud import get_user_by_email
from security.unique_id import generate_unique_id
from security.jwt_token import generate_jwt_token
from security.jwt_token import generate_jwt_token
import jwt
from icecream import ic
import secrets
from hashlib import sha256
from dotenv import load_dotenv
import os
load_dotenv()
from urllib.parse import urlencode
import requests
import httpx
from utils.redirectcode_genereator import generate_redirect_code
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink,redis_curttl
from exceptions.session_exp import SessionExpired
from utils.url_secret_generator import verify_url_secret
GOOGLE_REDIRECT_URI=f"{os.getenv("REDIRECT_BASEURL")}/auth/google/callback"
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")

router=APIRouter(
    tags=["Google Authentication"]
)

@router.get("/auth/google/login/{auth_token}")
async def google_login(request:Request,auth_token:str):
    verified_secret:dict=verify_url_secret(url_secret=auth_token,cur_ip=request.client.host) or {}
    auth_id:str=verified_secret.get('auth_id')

    if not await redis_get(auth_id):
        ic("Invalid Auth Id")
        raise SessionExpired(redirect_url=verified_secret.get("redirect_url",'/'))
    
    state=generate_unique_id("google") 
    await redis_set(key=state,value=auth_token,exp=120)
    ic(auth_id)

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        'state': state,
    }

    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=google_auth_url,status_code=302)


@router.get("/auth/google/callback")
async def google_callback(request:Request,code: str,state: str):
    ic(code,state)
    auth_token=await redis_get(state) or ''
    await redis_unlink(state)
    verified_secret:dict=verify_url_secret(url_secret=auth_token,cur_ip=request.client.host) or {}
    auth_id:str=verified_secret.get('auth_id')
    
    if not auth_id:
        ic("Invalid State Parameter")
        raise SessionExpired(
            redirect_url=verified_secret.get("redirect_url",'/'),
            message="Session Expired redirecting to DeB-Auth-Service"
        )
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as http:
        resp = await http.post(token_url, data=data)
        
    if resp.status_code != 200:
        raise HTTPException(400, "Failed to get token from Google")
    
    token_data:dict = resp.json()
    id_token = token_data.get("id_token")
    ic(id_token)
    
    user_info:dict = jwt.decode(id_token, options={"verify_signature": False})
    email = user_info.get("email")
    name = user_info.get("name")
    profile_picture = user_info.get("picture")

    return await generate_redirect_code(
        auth_id=auth_id,
        auth_user={
            'email':email,
            'name':name,
            'profile_picture':profile_picture
        }
    )
