import secrets
from hashlib import sha256
from globals import authenticated_dict
from security.jwt_token import generate_jwt_token
from icecream import ic
from fb_database.operations.users_crud import get_user_by_email

def generate_redirect_code(cur_auth_user:dict):
    suffix_token=secrets.token_urlsafe(10)
    code=sha256(get_user_by_email(cur_auth_user['user_id']).get('client_secret').encode()).hexdigest()[:10]+suffix_token
    ic(code)
    authenticated_dict[code]={
        'token':generate_jwt_token(
            {
                'email': cur_auth_user['email'],
                'name': cur_auth_user['full_name'],
                'profile_picture': None
            }
        ),
        'suffix_token':suffix_token
    }

    return code