from ..models.user_model import UserDropDownsModel,UserRedirectModel,UserSecretsModel,UserSettingsModel,UserSignupFieldsModel,UsersModel
from schemas.request_schemas.auth_schema import *
from schemas.request_schemas.redirect_schema import CreateRedirectSchema,BaseRedirectSchema
from schemas.request_schemas.ui_schema import CreateUiSchema,UpdateUiSchema
from schemas.request_schemas.user_client_schema import UserClientDeviceInfos
from schemas.db_schemas.user_schema import CreateRedirectSchema,CreateUserDbSchema,CreateUserDropDownDbSchemas,CreateUserRedirectDbSchema,CreateUserSecretDbSchema,CreateUserSettingDbSchema,CreateUserSignupFieldsSchema,UpdateUserDbSchema,UpdateUserDropDownDbSchema,UpdateUserRedirectDbSchema,UpdateUserSecretDbSchema,UpdateUserSettingDbSchema,UpdateUserSignupFieldDbSchema,GetUserSignUpFieldsDbSchema,GetUserDbSchema,GetUserDropDownDbSchema,GetUserRedirectDbSchema,GetUserSecretDbSchema,GetUserSettingDbSchema,DeleteUserSignUpFieldsDbSchema,DeleteUserDbSchema,DeleteUserDropDownDbSchema,DeleteUserRedirectDbSchema,DeleteUserSecretDbSchema,DeleteUserSettingDbSchema,UserDropDownEntityEnum,GetUserByIdSchema,GetUserDropDownByIdSchema,GetUserRedirectByIdDbSchema,GetUserSecretByIdSchema,GetuserSettingByIdDbSchema,GetUserDropDownByUserSchema,GetUserRedirectByUserDbSchema,GetUserSecretByUserSchema,GetUserSettingByUserDbSchema,GetUserSignUpFielsByIdDbSchema,GetUserSignUpFielsByUserDbSchema
from typing import Optional,List
from icecream import ic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select,update,delete,Select


class UserRepo:
    def __init__(self,session:AsyncSession):
        self.session=session
        self.user_cols=(
            UsersModel.id,
            UsersModel.name,
            UsersModel.mobile_number,
            UsersModel.created_at,
            UsersModel.updated_at
        )

    async def create_user(self,data:CreateUserDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    insert(
                        UsersModel
                    )
                    .values(
                        **data.model_dump(mode="json")
                    )
                    .returning(
                        *self.user_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while Creating user => {e}")
                return False

        

    

    
    async def update_user(self,data:UpdateUserDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    update(
                        UsersModel
                    )
                    .where(
                        UsersModel.id==data.id,
                    )
                    .values(
                        **data.model_dump(mode="json",exclude=['id','email'],exclude_none=True,exclude_unset=True)
                    )
                    .returning(
                        *self.user_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while Updating User => {e}")
                return False

    
    
    async def delete_user(self,data:DeleteUserDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    delete(
                        UsersModel
                    )
                    .where(
                        UsersModel.id==data.id
                    )
                    .returning(*self.user_cols)
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erro while deleting user => {e}")
                return False


    

    async def get_user(self,data:GetUserDbSchema)-> List[dict] | list:
        async with self.session.begin():
            try:
                cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
                stmt=(
                    select(
                        *self.user_cols
                    )
                    .offset(offset=cursor)
                    .limit(limit=data.limit)
                )

                res=(await self.session.execute(stmt)).mappings().all()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erorr while getting user => {e}")
                return False


            
    async def get_user_by_id(self,data:GetUserByIdSchema) -> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    select(
                        *self.user_cols
                    )
                    .where(
                        UsersModel.id==data.id
                    )  
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res

            except Exception as e:
                ic(f"Erorr while geting user by id => {e}")
                return False