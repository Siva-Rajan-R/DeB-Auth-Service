from fastapi import APIRouter,HTTPException
from fastapi.responses import RedirectResponse
from fb_database.operations.users_crud import get_user_by_email
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
import requests
from globals import auth_dict,authenticated_dict,STATE_STORE

GITHUB_CLIENT_ID=os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET=os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI="http://127.0.0.1:8000/auth/github/callback"

router=APIRouter(
    tags=["GitHub Authentication"]
)
@router.get("/auth/github/login/{auth_id}")
def github_login(auth_id:str):

    if not auth_dict.get(auth_id,False):
        raise HTTPException(
            status_code=404,
            detail="invalid auth id"
        )
    
    state = generate_unique_id("github")
    STATE_STORE[state] = auth_id

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": state,
    }

    github_auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=github_auth_url,status_code=302)

@router.get("/auth/github/callback")
def github_login_callback(code: str, state: str):
    if not STATE_STORE.get(state):
        raise HTTPException(400, "Invalid state parameter")

    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "state": state,
    }

    resp = requests.post(token_url, data=data, headers=headers)
    token_data = resp.json()
    ic(token_data)
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(400, "Failed to get access token from GitHub")

    user_resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {access_token}"}
    )
    user_info = user_resp.json()

    email_resp = requests.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"token {access_token}"}
    )
    emails = email_resp.json()
    primary_email = None
    ic(emails)
    if isinstance(emails, list):
        for e in emails:
            if e.get("primary") and e.get("verified"):
                primary_email = e.get("email")

    suffix_token=secrets.token_urlsafe(10)
    ic(auth_dict)
    extracted_auth_dict=auth_dict[STATE_STORE[state]]
    secret=get_user_by_email(extracted_auth_dict['user_id']).get('secrets',[])
    client_secret=secret.get(extracted_auth_dict['apikey'],None)

    if not client_secret:
        raise HTTPException(
            status_code=403,
            detail="client secret not found"
        )
    auth_code=sha256(client_secret.encode()).hexdigest()[:10]+suffix_token

    app_token = generate_jwt_token({
        "email": primary_email,
        "name": user_info.get("name") or user_info.get("login"),
        'profile_picture': user_info.get("avatar_url"),
    },exp_min=60)
    authenticated_dict[auth_code]={'token':app_token,'suffix_token':suffix_token,'user_id':extracted_auth_dict['user_id'],'apikey':extracted_auth_dict['apikey']}
    del STATE_STORE[state]
    ic(app_token)

    return RedirectResponse(url=f"{extracted_auth_dict['redirect_url']}?code={auth_code}", status_code=302)



