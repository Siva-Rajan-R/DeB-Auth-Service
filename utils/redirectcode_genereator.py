from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
import secrets
from hashlib import sha256
from security.jwt_token import generate_jwt_token
from icecream import ic
from operations.fb_operations.users_crud import get_user_by_email
from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink,redis_curttl

async def generate_redirect_code(auth_user:dict,auth_id:str,isfor_otp:bool=False):
    extracted_auth_dict=auth_user
    if not isfor_otp:
        extracted_auth_dict=await redis_get(auth_id)

    await redis_unlink(auth_id)
    ic(extracted_auth_dict)
    suffix_token=secrets.token_urlsafe(10)
    secret:dict=get_user_by_email(extracted_auth_dict['config']['user_email']).get('secrets',{})
    client_secret:str=secret.get(extracted_auth_dict['apikey'],None)

    if not client_secret:
        raise HTTPException(
            status_code=403,
            detail="client secret not found"
        )
    
    auth_code=sha256(client_secret.encode()).hexdigest()[:10]+suffix_token

    app_token = generate_jwt_token({
        "email": auth_user['email'],
        "name": auth_user['name'],
        'profile_picture': auth_user['profile_picture'],
    },exp_min=60)

    authenticated_values={
        'token':app_token,
        'suffix_token':suffix_token,
        'user_email':extracted_auth_dict['config']['user_email'],
        'apikey':extracted_auth_dict['apikey']
    }
    await redis_set(key=auth_code,value=authenticated_values,exp=540)
    return RedirectResponse(url=f"{extracted_auth_dict['config']['redirect_url']}?code={auth_code}", status_code=302)