import string
import random
from configs.settings import settings

def generate_otp(len:int=6):
    if settings.MOCK_MODE:
        return settings.MOCK_OTP
    return ''.join(random.choices(string.digits,k=len))