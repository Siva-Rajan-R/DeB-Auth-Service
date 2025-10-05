from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import RedirectResponse
from operations.fb_operations.users_crud import get_user_by_email
from security.unique_id import generate_unique_id
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

GITHUB_CLIENT_ID=os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET=os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI=f"{os.getenv("REDIRECT_BASEURL")}/auth/github/callback"

router=APIRouter(
    tags=["GitHub Authentication"]
)
@router.get("/auth/github/login/{auth_token}")
async def github_login(request:Request,auth_token:str):
    verified_secret:dict=verify_url_secret(url_secret=auth_token,cur_ip=request.client.host) or {}
    auth_id:str=verified_secret.get('auth_id')

    if not await redis_get(auth_id):
        ic("Invalid Auth id")
        raise SessionExpired(redirect_url=verified_secret.get("redirect_url",'/'))
    
    state = generate_unique_id("github")
    await redis_set(key=state,value=auth_token,exp=120)

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": state,
    }

    github_auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=github_auth_url,status_code=302)

@router.get("/auth/github/callback")
async def github_login_callback(request:Request,code: str, state: str):
    auth_token=await redis_get(state) or ''
    await redis_unlink(state)
    verified_secret:dict=verify_url_secret(url_secret=auth_token,cur_ip=request.client.host) or {}
    auth_id:str=verified_secret.get('auth_id')
    

    if not auth_id:
        ic("invalid State Parameter")
        raise SessionExpired(
            redirect_url=verified_secret.get("redirect_url",'/'),
            message="Session Expired redirecting to DeB-Auth-Service"
        )

    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "state": state,
    }

    async with httpx.AsyncClient() as http:
        resp = await http.post(token_url, data=data, headers=headers)
        token_data = resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(400, "Failed to get access token from GitHub")

        user_resp = await http.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"}
        )

        user_info:dict = user_resp.json()

        email_resp = await http.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"token {access_token}"}
        )

        emails = email_resp.json()

    primary_email = None
    ic(emails,user_info)
    if isinstance(emails, list):
        for e in emails:
            if e.get("primary") and e.get("verified"):
                primary_email = e.get("email")
    email=primary_email
    user_name=user_info.get("name") or user_info.get("login")
    profile_pic=user_info.get("avatar_url")
    
    return await generate_redirect_code(
        auth_id=auth_id,
        auth_user={
            'email':email,
            'name':user_name,
            'profile_picture':profile_pic
        }
    )



