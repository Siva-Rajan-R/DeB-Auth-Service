from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import RedirectResponse
from operations.fb_operations.users_crud import get_user_by_email
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
@router.get('/auth/github/login/{request_id}')
async def github_login(request: Request, request_id: str):
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

        user_resp = await http.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"}
        )

        user_info:dict = user_resp.json()

        email_resp = await http.get(
            "https://github.com/user/emails",
            headers={"Authorization": f"token {access_token}"}
        )

        emails = email_resp.json()

    primary_email = None
    if isinstance(emails, list):
        for e in emails:
            if e.get("primary") and e.get("verified"):
                primary_email = e.get("email")
    
    auth_user = {
        'email': primary_email or user_info.get("email"),
        'name': user_info.get('name') or user_info.get('login'),
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
