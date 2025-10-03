from fastapi import APIRouter,HTTPException
from fastapi.responses import RedirectResponse
from fb_database.operations.users_crud import get_user_by_email
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
import requests
from globals import auth_dict,authenticated_dict,STATE_STORE

FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
FACEBOOK_REDIRECT_URI = "http://localhost:8000/auth/facebook/callback"

router=APIRouter(
    tags=["Facebook Authentication"]
)


@router.get("/auth/facebook/login/{auth_id}")
def facebook_login(auth_id:str):
    if not auth_dict.get(auth_id,False):
        raise HTTPException(
            status_code=404,
            detail="invalid auth id"
        )
    
    state = generate_unique_id("facebook")
    STATE_STORE[state] = auth_id
    
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
def facebook_callback(code: str, state: str):
    if not STATE_STORE.get(state):
        raise HTTPException(400, "Invalid state")

    token_url = "https://graph.facebook.com/v20.0/oauth/access_token"
    token_params = {
        "client_id": FACEBOOK_CLIENT_ID,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "client_secret": FACEBOOK_CLIENT_SECRET,
        "code": code
    }
    token_resp = requests.get(token_url, params=token_params)
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
    user_resp = requests.get(user_info_url, params=user_params)
    user_data = user_resp.json()
    
    app_token = generate_jwt_token(
        {
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "profile_picture": user_data.get("picture", {}).get("data", {}).get("url")
        },
        exp_min=60
    )

    suffix_token=secrets.token_urlsafe(10)
    extracted_auth_dict=auth_dict[STATE_STORE[state]]

    secret=get_user_by_email(extracted_auth_dict['user_id']).get('secrets',[])
    client_secret=secret.get(extracted_auth_dict['apikey'],None)

    if not client_secret:
        raise HTTPException(
            status_code=403,
            detail="client secret not found"
        )
    auth_code=sha256(client_secret.encode()).hexdigest()[:10]+suffix_token

    authenticated_dict[auth_code]={'token':app_token,'suffix_token':suffix_token,'user_id':extracted_auth_dict['user_id'],'apikey':extracted_auth_dict['apikey']}
    del STATE_STORE[state]

    return RedirectResponse(url=f"{extracted_auth_dict['redirect_url']}?code={auth_code}", status_code=302)