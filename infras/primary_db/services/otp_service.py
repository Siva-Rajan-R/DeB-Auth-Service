from pydantic import BaseModel
from typing import Optional,List
from core.security.otp import generate_otp
from icecream import ic



class OtpService:
    @staticmethod
    async def create_otp(length:int=6):
        generated_otp=generate_otp(len=length)
        ic(generated_otp)
        return generated_otp
    

    @staticmethod
    async def verify_otp(alloc_otp:str,recv_otp:str):
        ic(recv_otp,alloc_otp)
        if alloc_otp!=recv_otp:
            ic("Otp verficition false inalid otp")
            return False
        
        return True