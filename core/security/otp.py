import string
import random

def generate_otp(len:int=6):
    return ''.join(random.choices(string.digits,k=len))