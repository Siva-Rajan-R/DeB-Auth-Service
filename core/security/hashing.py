from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


ph=PasswordHasher()

def hash_data(data:str)->str:
    try:
        return ph.hash(data)
    except Exception as e:
        raise RuntimeError(f"something went wrog while hasing data {e}")
    
def verify_hashed_data(hashed_data:str,plain_data:str)->bool:
    try:
        return ph.verify(hash=hashed_data,password=plain_data)
    
    except VerifyMismatchError:
        return False
    
    except Exception as e:
        raise RuntimeError(f"something went wrong while verifying hash {e}")
    