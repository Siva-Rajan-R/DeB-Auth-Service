from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import RedirectResponse
from operations.fb_operations.users_crud import get_user_by_email
from core.security.unique_id import generate_unique_id
from core.security.jwt_token import generate_jwt_token
from core.security.jwt_token import generate_jwt_token
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
from api.dependencies.auth_state import get_and_validate_auth_state
import json
GOOGLE_REDIRECT_URI=f"{os.getenv("REDIRECT_BASEURL")}/auth/google/callback"
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")

router=APIRouter(
    tags=["Google Authentication"]
)

@router.get("/auth/google/login/{request_id}")
async def google_login(request: Request, request_id: str):
    state = await get_and_validate_auth_state(request, request_id, required_step="device_validation")
    
    if "provider_selection" not in state.completed_steps:
        state.completed_steps.append("provider_selection")
    
    state.current_step = "authentication"
    if "authentication_started" not in state.completed_steps:
        state.completed_steps.append("authentication_started")
        
    await redis_set(key=request_id, value=state.model_dump(), exp=300)
    
    oauth_state_data = {"request_id": request_id}
    oauth_state_str = json.dumps(oauth_state_data)
    ic(request_id)

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        'state': oauth_state_str,
    }

    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=google_auth_url,status_code=302)


@router.get("/auth/google/callback")
async def google_login_callback(request:Request,code: str, state: str):
    try:
        oauth_state_data = json.loads(state)
        request_id = oauth_state_data.get("request_id")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
        
    auth_state = await get_and_validate_auth_state(request, request_id, required_step="authentication_started")
    
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
    
    auth_user = {
        'email': user_info['email'],
        'name': user_info.get('name'),
        'profile_picture': user_info.get('picture'),
        'custom_fields': auth_state.auth_data.get('custom_fields', {}),
        'config': auth_state.config,
        'apikey': auth_state.client_id,
        'flow_type': auth_state.flow_type,
        'auth_provider': 'google'
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
