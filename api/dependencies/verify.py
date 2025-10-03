from fastapi import Request,HTTPException
from security.sym_encrypt import decrypt_data
from security.jwt_token import verfiy_jwt_token
from dotenv import load_dotenv
from icecream import ic
import os,json
load_dotenv()

def verify_user(request:Request):
    try:
        token=request.cookies.get('token')
        # token=None
        ic(request.cookies)

        if not token:
            raise HTTPException(
                status_code=401,
                detail={'msg':'token not found','logout':True}
            )
        decoded_token=verfiy_jwt_token(
            jwt_token=token,
            key=os.getenv('DEB_USER_JWT_KEY'),
            alg=os.getenv('DEB_USER_JWT_ALGORITHM')
        )

        ic(decoded_token)
        if not decoded_token:
            raise HTTPException(
                status_code=401,
                detail={'msg':'Invalid token','logout':True}
            )
        
        decrypted_token=decrypt_data(
            data=decoded_token['data']
        )

        ic(decrypted_token) 
        if not decrypted_token:
            raise HTTPException(
                status_code=401,
                detail={'msg':'verification mismatch','logout':True}
            )
        
        return json.loads(decrypted_token)['user_email']
    
    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'something went wrong while verify user : {e}'
        )