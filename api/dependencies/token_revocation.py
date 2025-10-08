from security.jwt_token import generate_jwt_token,verfiy_jwt_token
from fastapi.requests import Request
from fastapi.exceptions import HTTPException
from icecream import ic
import os,json
from dotenv import load_dotenv
from security.sym_encrypt import decrypt_data,encrypt_data
load_dotenv() 


DEB_USER_JWT_ALGORITHM=os.getenv("DEB_USER_JWT_ALGORITHM","HS256")
DEB_USER_JWT_KEY=os.getenv("DEB_USER_JWT_KEY")
DEB_USER_REFRESH_JWT_ALGORITHM=os.getenv("DEB_USER_REFRESH_JWT_ALGORITHM")
DEB_USER_REFRESH_KEY=os.getenv("DEB_USER_REFRESH_KEY")

def revoke_user(request:Request):
    try:
        bearer_token=request.headers.get("authorization")
        if 'Bearer' not in bearer_token:
            raise HTTPException(
                status_code=422,
                detail="Invalid token type"
            )
        bearer,token = bearer_token.split(' ')
        ic(bearer,token)
        verified_refresh_token=verfiy_jwt_token(jwt_token=token,key=DEB_USER_REFRESH_KEY,alg=DEB_USER_REFRESH_JWT_ALGORITHM)
        ic(verified_refresh_token)
        decrypted_token=decrypt_data(verified_refresh_token['data'])
        ic(decrypted_token)
        if not decrypted_token:
            raise HTTPException(
                status_code=401, 
                detail={'msg':'Invalid Data','logout':True}
            )
        
        access_token=generate_jwt_token(
            data={'data':encrypt_data(json.dumps({'user_email':json.loads(decrypted_token)['user_email']}))},
            exp_min=15,
            alg=DEB_USER_JWT_ALGORITHM,
            key=DEB_USER_JWT_KEY
        )

        if access_token:
            return access_token
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while verifying token {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while verifying token {e}"
        )