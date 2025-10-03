from fastapi import APIRouter,HTTPException
from fastapi.responses import RedirectResponse
from fb_database.operations.users_crud import get_user_by_email
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
from globals import auth_dict,authenticated_dict,STATE_STORE

GOOGLE_REDIRECT_URI="http://127.0.0.1:8000/auth/google/callback"
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")

router=APIRouter(
    tags=["Google Authentication"]
)

@router.get("/auth/google/login/{auth_id}")
def google_login(auth_id:str):
    if not auth_dict.get(auth_id,False):
        raise HTTPException(
            status_code=404,
            detail="invalid auth id"
        )
    
    state=generate_unique_id("google") 
    STATE_STORE[state]=auth_id
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
def google_callback(code: str,state: str):
    ic(code,state)
    if not STATE_STORE.get(state,False):
        raise HTTPException(400, "Invalid state parameter") 

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    resp = requests.post(token_url, data=data)
    if resp.status_code != 200:
        raise HTTPException(400, "Failed to get token from Google")
    
    token_data = resp.json()
    id_token = token_data.get("id_token")

    extracted_auth_dict=auth_dict[STATE_STORE[state]]
    ic(extracted_auth_dict)
    suffix_token=secrets.token_urlsafe(10)
    secret=get_user_by_email(extracted_auth_dict['user_id']).get('secrets',[])
    client_secret=secret.get(extracted_auth_dict['apikey'],None)
    if not client_secret:
        raise HTTPException(
            status_code=403,
            detail="client secret not found"
        )
    auth_code=sha256(client_secret.encode()).hexdigest()[:10]+suffix_token
    ic(id_token)
    user_info = jwt.decode(id_token, options={"verify_signature": False})
    email = user_info.get("email")
    name = user_info.get("name")
    profile_picture = user_info.get("picture")

    app_token = generate_jwt_token({
        "email": email,
        "name": name,
        'profile_picture': profile_picture,
    },exp_min=60)

    authenticated_dict[auth_code]={'token':app_token,'suffix_token':suffix_token,'user_id':extracted_auth_dict['user_id'],'apikey':extracted_auth_dict['apikey']}
    del STATE_STORE[state]
    return RedirectResponse(url=f"{extracted_auth_dict['redirect_url']}?code={auth_code}", status_code=302)
