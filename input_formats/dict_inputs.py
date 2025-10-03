from typing import TypedDict
from pydantic import EmailStr
from typing import List,Optional
from .enum_inputs import AuthMethods


class Configuration(TypedDict):
    redirect_url:str
    branding:Optional[str]="De-Buggers"
    auth_methods:List[AuthMethods]


class User(TypedDict):
    name:str
    email:EmailStr
    secrets:dict
    remove_branding:bool
    max_keys:int=2
