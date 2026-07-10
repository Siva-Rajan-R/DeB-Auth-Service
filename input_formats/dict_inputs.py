from typing import TypedDict
from pydantic import EmailStr
from typing import List,Optional
from .enum_inputs import AuthMethods


class Configuration(TypedDict, total=False):
    project_name: Optional[str]
    redirect_urls: dict
    branding: Optional[str]
    auth_methods: List[dict]
    signup_fields: Optional[List[dict]]
    sso: Optional[dict]
    ui: Optional[dict]
    two_factor: Optional[dict]


class User(TypedDict):
    name:str
    email:EmailStr
    secrets:dict
    remove_branding:bool
    max_keys:int=2
