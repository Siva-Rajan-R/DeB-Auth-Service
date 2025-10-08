from jwt import PyJWT
from fastapi.exceptions import HTTPException
from jwt.exceptions import InvalidTokenError,ExpiredSignatureError
from datetime import datetime,timedelta,timezone
from dotenv import load_dotenv
import os
from icecream import ic
load_dotenv()


pyjwt_obj=PyJWT()

JWT_ALG=os.getenv("JWT_ALGORITHM")
JWT_KEY=os.getenv("JWT_KEY")


def generate_jwt_token(data:dict,exp_min:int=0,exp_sec:int=0,exp_days:int=0,alg:str=JWT_ALG,key:str=JWT_KEY)->str:
    try:
        if exp_min==0 and exp_sec==0 and exp_days==0:
            raise ValueError("only one of exp_min,exp_sec,exp_days should be provided")
        data['iss']="DeB-Auth-Service"
        data['iat']=datetime.now(timezone.utc)
        data['exp']=datetime.now(timezone.utc)+timedelta(minutes=exp_min,seconds=exp_sec,days=exp_days)
        return pyjwt_obj.encode(payload=data,key=key,algorithm=alg)
    
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"something went wrong while gwnrating jwt token {e}")

def verfiy_jwt_token(jwt_token:str,key:str=JWT_KEY,alg:str=JWT_ALG):
    try:
        return pyjwt_obj.decode(jwt=jwt_token,key=key,algorithms=alg)
    
    except InvalidTokenError:
        ic({'msg':"Invalid token",'logout':True})
        raise HTTPException(
            status_code=401,
            detail={'msg':"Invalid token",'logout':True}
        )
    
    except ExpiredSignatureError:
        ic({'msg':"Invalid token or token expierd",'expired':True})
        raise HTTPException(
            status_code=401,
            detail={'msg':"Invalid token or token expierd",'logout':True}
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise RuntimeError(f"something went wrong while verifying jwt token {e}")
    
# print(generate_jwt_token({'user_id':1234}))
# print(verfiy_jwt_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjM0LCJleHAiOjE3NTU5NDk1Njh9.pQuT7V61IewXJUfD92Rj8mhCcJxsXapIlI8uz-wJ30Q"))

