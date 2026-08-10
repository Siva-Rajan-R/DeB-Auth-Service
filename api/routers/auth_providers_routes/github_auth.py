from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import RedirectResponse
from operations.mongo_operations.users_crud import get_user_by_email
from core.security.unique_id import generate_unique_id
from core.security.jwt_token import generate_jwt_token
from core.security.jwt_token import generate_jwt_token
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
from api.dependencies.auth_state import get_and_validate_auth_state
import json

GITHUB_CLIENT_ID=os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET=os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI=f"{os.getenv("REDIRECT_BASEURL")}/auth/github/callback"

router=APIRouter(
    tags=["GitHub Authentication"]
)
@router.get('/auth/github/login/{auth_token}')
async def github_login(request: Request, auth_token: str):
    verified_secret: dict = verify_url_secret(url_secret=auth_token, request=request) or {}
    request_id: str = verified_secret.get('auth_id')
    if not request_id or not await redis_get(request_id):
        raise SessionExpired(redirect_url=verified_secret.get("redirect_url", '/'))

    state = await get_and_validate_auth_state(request, request_id, required_step="device_validation")
    
    if "provider_selection" not in state.completed_steps:
        state.completed_steps.append("provider_selection")
    
    state.current_step = "authentication"
    if "authentication_started" not in state.completed_steps:
        state.completed_steps.append("authentication_started")
        
    await redis_set(key=request_id, value=state.model_dump(), exp=300)
    
    oauth_state_data = {"request_id": request_id}
    oauth_state_str = json.dumps(oauth_state_data)

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": oauth_state_str,
    }

    github_auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=github_auth_url,status_code=302)

@router.get('/auth/github/callback')
async def github_callback(request: Request, code: str, state: str):
    try:
        oauth_state_data = json.loads(state)
        request_id = oauth_state_data.get("request_id")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
        
    auth_state = await get_and_validate_auth_state(request, request_id, required_step="authentication_started")

    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as http:
        resp = await http.post(token_url, data=data, headers=headers)
        token_data = resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(400, "Failed to get access token from GitHub")

        user_headers = {
            "Authorization": f"token {access_token}",
            "User-Agent": "DAuth-App",
            "Accept": "application/json"
        }

        user_resp = await http.get("https://api.github.com/user", headers=user_headers)
        user_info: dict = user_resp.json() if user_resp.status_code == 200 else {}

        email_resp = await http.get("https://api.github.com/user/emails", headers=user_headers)
        emails = email_resp.json() if email_resp.status_code == 200 else []

    primary_email = None
    if isinstance(emails, list):
        for e in emails:
            if e.get("primary") and e.get("verified"):
                primary_email = e.get("email")
                break
        if not primary_email and len(emails) > 0:
            primary_email = emails[0].get("email")
    
    email_val = primary_email or user_info.get("email") or ""
    raw_name = user_info.get('name') or user_info.get('login')
    if not raw_name or str(raw_name).strip() in ['', 'None', 'null', 'undefined']:
        user_name = email_val.split('@')[0] if email_val and '@' in email_val else 'GitHub User'
    else:
        user_name = str(raw_name).strip()

    auth_user = {
        'email': email_val,
        'name': user_name,
        'profile_picture': user_info.get('avatar_url'),
        'custom_fields': auth_state.auth_data.get('custom_fields', {}),
        'config': auth_state.config,
        'apikey': auth_state.client_id,
        'flow_type': auth_state.flow_type,
        'auth_provider': 'github'
    }
    
    auth_state.status = "completed"
    await redis_set(key=request_id, value=auth_state.model_dump(), exp=300)
    
    return await generate_redirect_code(
        auth_id=request_id,
        auth_user=auth_user,
        isfor_otp=True,
        request=request,
        return_json=False
    )
