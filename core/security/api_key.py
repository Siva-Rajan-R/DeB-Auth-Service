import secrets

def generate_api_key(key_prefix:str="DeB-",key_length:int=32)->str:
    return key_prefix+secrets.token_urlsafe(key_length)
