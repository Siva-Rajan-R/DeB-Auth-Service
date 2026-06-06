from pydantic import BaseModel
from typing import Optional,List


class BaseRedirectSchema(BaseModel):
    success_redirect_url:str
    failure_redirect_url:str



class CreateRedirectSchema(BaseModel):
    sign_in:BaseRedirectSchema
    sign_up:BaseRedirectSchema
