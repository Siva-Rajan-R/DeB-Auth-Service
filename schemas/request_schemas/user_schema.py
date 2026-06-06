from pydantic import BaseModel,Field,EmailStr
from typing import Optional,List
from ..request_schemas.redirect_schema import CreateRedirectSchema,BaseRedirectSchema
from ..request_schemas.fields_schema import SignUpFieldSchema
from core.data_formats.enums.user_enum import UserDropDownEntityEnum


# User Schemas
class CreateUserSchema(BaseModel):
    name:str
    email:EmailStr
    mobile_number:Optional[str]=None

class UpdateUserSchema(BaseModel):
    id:str
    name:Optional[str]=None
    mobile_number:Optional[str]=None

class DeleteUserSchema(BaseModel):
    id:str

class GetUserSchema(BaseModel):
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)

class GetUserByIdSchema(BaseModel):
    id:str


# User Seceret Schemas



# User settings Modal
class CreateUserSettingSchema(BaseModel):
    user_id:str
    sso_enabled:Optional[bool]=False

class UpdateUserSettingDbSchema(BaseModel):
    id:str
    user_id:str
    sso_enabled:Optional[bool]=False

class DeleteUserSettingDbSchema(BaseModel):
    id:str
    user_id:str

class GetUserSettingDbSchema(BaseModel):
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)

class GetUserSettingByUserDbSchema(BaseModel):
    user_id:str
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)

class GetuserSettingByIdDbSchema(BaseModel):
    id:str
    user_id:str
    



# User Redirect Models
class CreateUserRedirectDbSchema(BaseModel):
    id:str
    user_id:str
    sign_in:BaseRedirectSchema
    sign_up:BaseRedirectSchema

class UpdateUserRedirectDbSchema(BaseModel):
    id:str
    user_id:str
    sign_in:Optional[BaseRedirectSchema]=None
    sign_up:Optional[BaseRedirectSchema]=None

class DeleteUserRedirectDbSchema(BaseModel):
    id:str
    user_id:str

class GetUserRedirectDbSchema(BaseModel):
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)

class GetUserRedirectByIdDbSchema(BaseModel):
    id:str
    user_id:str

class GetUserRedirectByUserDbSchema(BaseModel):
    user_id:str
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)


# User Signup Fields Schema
class CreateUserSignupFieldsSchema(BaseModel):
    id:str
    user_id:str
    fields:SignUpFieldSchema

class UpdateUserSignupFieldDbSchema(BaseModel):
    id:str
    user_id:str
    fields:Optional[SignUpFieldSchema]=None

class DeleteUserSignUpFieldsDbSchema(BaseModel):
    id:str
    user_id:str

class GetUserSignUpFieldsDbSchema(BaseModel):
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)

class GetUserSignUpFielsByIdDbSchema(BaseModel):
    id:str
    user_id:str

class GetUserSignUpFielsByUserDbSchema(BaseModel):
    user_id:str
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)




# User Dropdown Schemas
class CreateUserDropDownDbSchemas(BaseModel):
    id:str
    user_id:str
    roles:List[str]

class UpdateUserDropDownDbSchema(BaseModel):
    id:str
    user_id:str
    roles:Optional[List[str]]=None

class DeleteUserDropDownDbSchema(BaseModel):
    id:str
    user_id:str
    entity:UserDropDownEntityEnum

class GetUserDropDownDbSchema(BaseModel):
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)

class GetUserDropDownByIdSchema(BaseModel):
    id:str
    user_id:str

class GetUserDropDownByUserSchema(BaseModel):
    user_id:str
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)
