from cryptography.fernet import Fernet
from cryptography.exceptions import InvalidSignature
from dotenv import load_dotenv
import os
load_dotenv()

SYMME_KEY=os.getenv("SYMMETRIC_KEY_SECRET")
fernet_obj=Fernet(SYMME_KEY.encode())

def encrypt_data(data:str)->str:
    try:
        return fernet_obj.encrypt(data=data.encode()).decode()
    except Exception as e:
        raise RuntimeError(f"something went wrong while encrypting data {e}")
    
def decrypt_data(data:str)->str:
    try:
        return fernet_obj.decrypt(data.encode()).decode()
    except InvalidSignature:
        return "invalid data"
    except Exception as e:
        raise RuntimeError(f"something went wrong while decrypting data {e}")
    
# print(encrypt_data("siva"))
# print(decrypt_data("gAAAAABoqZ5fD_7Ns4WL6phhm0W27GwzNWnD-wfXnxAWX1-RWit4prqLHNkky42UO7m6OCHRl6Ve0zn0ValeXjQ30Kpe3X1XCw=="))
