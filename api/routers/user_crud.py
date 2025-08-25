from fastapi import APIRouter
from security.unique_id import generate_unique_id
from security.api_key import generate_api_key
from pydantic import BaseModel,EmailStr
from input_formats.dict_inputs import User
from fb_database.operations.users_crud import create_user,get_user_by_id,get_all_users,delete_user


router=APIRouter(
    tags=["User CRUD"]
)

class UserSchema(BaseModel):
    name:str
    email:EmailStr

class UserDeleteSchema(BaseModel):
    user_id:str

@router.post("/users")
def create_users(user:UserSchema):
    pk=generate_unique_id(user.name)
    apikey=generate_api_key()
    client_secret=generate_api_key(key_prefix="DeB-Secret-",key_length=64)
    formatted_user=User(
        name=user.name,
        email=user.email,
        pk=pk,
        apikey=apikey,
        client_secret=client_secret
    )

    return create_user(formatted_user,pk,apikey,client_secret)

@router.get("/users/{user_pk}")
def get_user_by_pk(user_pk:str):
    return get_user_by_id(user_pk=user_pk)

@router.get("/users")
def get_users():
    return get_all_users()

@router.delete("/users")
def delete_users(user_id:UserDeleteSchema):
    return delete_user(user_pk=user_id.user_id)