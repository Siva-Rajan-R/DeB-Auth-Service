from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import RedirectResponse
from operations.fb_operations.users_crud import get_user_by_email
from security.unique_id import generate_unique_id
from security.otp import generate_otp
from security.jwt_token import generate_jwt_token
from security.jwt_token import generate_jwt_token
from icecream import ic
import secrets
from hashlib import sha256
from dotenv import load_dotenv
import os
load_dotenv()
from urllib.parse import urlencode
import httpx
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink,redis_curttl
from utils.redirectcode_genereator import generate_redirect_code
from exceptions.session_exp import SessionExpired
from utils.url_secret_generator import verify_url_secret

FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
FACEBOOK_REDIRECT_URI = f"{os.getenv("REDIRECT_BASEURL")}/auth/facebook/callback"

router=APIRouter(
    tags=["Facebook Authentication"]
)


@router.get("/auth/facebook/login/{auth_token}")
async def facebook_login(request:Request,auth_token:str):
    verified_secret:dict=verify_url_secret(url_secret=auth_token,cur_ip=request.client.host) or {}
    auth_id:str=verified_secret.get('auth_id')
    if not await redis_get(auth_id):
        ic("Invalid Auth Id")
        raise SessionExpired(redirect_url=verified_secret.get("redirect_url",'/'))
    
    state = generate_unique_id("facebook")
    await redis_set(key=state,value=auth_token,exp=120)
    
    params = {
        "client_id": FACEBOOK_CLIENT_ID,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "state": state,
        "scope": "email,public_profile",
        "response_type": "code"
    }

    fb_auth_url = f"https://www.facebook.com/v20.0/dialog/oauth?{urlencode(params)}"
    return RedirectResponse(url=fb_auth_url,status_code=302)


@router.get("/auth/facebook/callback")
async def facebook_callback(request:Request,code: str, state: str):
    auth_token=await redis_get(state) or ''
    await redis_unlink(state)
    verified_secret:dict=verify_url_secret(url_secret=auth_token,cur_ip=request.client.host) or {}
    auth_id:str=verified_secret.get('auth_id')
    
    if not auth_id:
        ic("inavlid State Parameter")
        raise SessionExpired(
            redirect_url=verified_secret.get("redirect_url",'/'),
            message="Session Expired redirecting to DeB-Auth-Service"
        )

    token_url = "https://graph.facebook.com/v20.0/oauth/access_token"
    token_params = {
        "client_id": FACEBOOK_CLIENT_ID,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "client_secret": FACEBOOK_CLIENT_SECRET,
        "code": code
    }

    async with httpx.AsyncClient() as http:
        token_resp = await http.get(token_url, params=token_params)
        token_data = token_resp.json()
        ic(token_data)
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "Failed to get access token")

        user_info_url = "https://graph.facebook.com/me"
        user_params = {
            "fields": "id,name,email,picture",
            "access_token": access_token
        }
        user_resp = await http.get(user_info_url, params=user_params)
        user_data = user_resp.json()
    
    email=user_data.get("email")
    name=user_data.get("name")
    profile_pic=user_data.get("picture", {}).get("data", {}).get("url")

    return await generate_redirect_code(
        auth_id=auth_id,
        auth_user={
            'email':email,
            'name':name,
            'profile_picture':profile_pic
        }
    )