from jwt import PyJWT
from jwt.exceptions import InvalidTokenError
from datetime import datetime,timedelta,timezone
from dotenv import load_dotenv
import os
load_dotenv()


pyjwt_obj=PyJWT()

JWT_ALG=os.getenv("JWT_ALGORITHM")
JWT_KEY=os.getenv("JWT_KEY")


def generate_jwt_token(data:dict,exp_min:int=60)->str:
    try:
        data['exp']=datetime.now(timezone.utc)+timedelta(minutes=exp_min)
        return pyjwt_obj.encode(payload=data,key=JWT_KEY,algorithm=JWT_ALG,)
    
    except Exception as e:
        raise RuntimeError(f"something went wrong while gwnrating jwt token {e}")

def verfiy_jwt_token(jwt_token:str):
    try:
        return pyjwt_obj.decode(jwt=jwt_token,key=JWT_KEY,algorithms=JWT_ALG)
    
    except InvalidTokenError:
        return "Invalid token or token expierd"
    
    except Exception as e:
        raise RuntimeError(f"something went wrong while verifying jwt token {e}")
    
# print(generate_jwt_token({'user_id':1234}))
# print(verfiy_jwt_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjM0LCJleHAiOjE3NTU5NDk1Njh9.pQuT7V61IewXJUfD92Rj8mhCcJxsXapIlI8uz-wJ30Q"))

