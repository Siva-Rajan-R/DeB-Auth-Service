from fastapi.exceptions import HTTPException
from itsdangerous import URLSafeSerializer
import os
from dotenv import load_dotenv
from icecream import ic
load_dotenv()


URL_SYM_KEY=os.getenv("URL_ENCODE_KEY")

auth_s=URLSafeSerializer(secret_key=URL_SYM_KEY)

def generate_url_secret(data):
    try:
        url_encoded=auth_s.dumps(data)
        ic(url_encoded)
        return url_encoded
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while generating url secret {e}")

def verify_url_secret(url_secret:str,cur_ip:str):
    try:
        url_decoded:dict=auth_s.loads(url_secret)
        ic(cur_ip)
        ic(url_decoded)
        if not url_decoded.get('ip','')==cur_ip:
            raise HTTPException(
                status_code=401,
                detail="Your Network was interprutted"
            )
        
        return url_decoded
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while verifying url secret {e}")
    


