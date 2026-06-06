from pydantic import BaseModel,EmailStr
from typing import Optional,List



class CreateLinkSchema(BaseModel):
    client_id:str

class GetUiInfoSchema(BaseModel):
    link_id:str


class AuthenticateSchema(BaseModel):
    link_id:str
    method:str
    email:Optional[EmailStr]=None