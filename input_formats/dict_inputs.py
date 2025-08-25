from typing import TypedDict
from pydantic import EmailStr


class User(TypedDict):
    pk:str
    name:str
    email:EmailStr
    apikey:str