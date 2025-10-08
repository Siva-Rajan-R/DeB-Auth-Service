from security.jwt_token import verfiy_jwt_token,generate_jwt_token
from security.sym_encrypt import decrypt_data,encrypt_data
from fastapi.requests import Request
from fastapi.exceptions import HTTPException
from icecream import ic
import os,json
from dotenv import load_dotenv
load_dotenv()


DEB_USER_JWT_ALGORITHM=os.getenv("DEB_USER_JWT_ALGORITHM","HS256")
DEB_USER_JWT_KEY=os.getenv("DEB_USER_JWT_KEY")
DEB_USER_REFRESH_JWT_ALGORITHM=os.getenv("DEB_USER_REFRESH_JWT_ALGORITHM")
DEB_USER_REFRESH_KEY=os.getenv("DEB_USER_REFRESH_KEY")


def verify_user(request:Request):
    try:
        bearer_token=request.headers.get("Authorization")
        if not bearer_token:
            raise HTTPException(
                status_code=401,
                detail="Authorization header missing"
            )
        
        ic(bearer_token)
        ic('here')
        if not bearer_token and 'Bearer' not in bearer_token:
            raise HTTPException(
                status_code=422,
                detail="Invalid token type"
            )
        bearer,token = bearer_token.split(' ')
        ic(bearer,token)
        verified_token=verfiy_jwt_token(jwt_token=token,key=DEB_USER_JWT_KEY,alg=DEB_USER_JWT_ALGORITHM)
        ic(verified_token)
        if verified_token:
            decrypted_data=decrypt_data(verified_token['data'])
            ic(decrypted_data)
            if not decrypted_data:
                raise HTTPException(
                    status_code=401,
                    detail={'msg':'Invalid Secrets','logout':True}
                )
            return json.loads(decrypted_data)['user_email']
        
    except HTTPException:
        raise

    except Exception as e: 
        ic(f"something went wrong while verifying token {e}")
        raise HTTPException(
            status_code=500,
            detail={'msg':f"something went wrong while verifying token {e}",'logout':True}
        )