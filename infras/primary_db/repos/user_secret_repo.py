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


class UserSecretRepo:
    def __init__(self,session:AsyncSession):
        self.session=session

        self.user_secret_cols=(
            UserSecretsModel.id,
            UserSecretsModel.user_id,
            UserSecretsModel.client_secret,
            UserSecretsModel.created_at
        )


    
    async def create_user_secret(self,data:CreateUserSecretDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    insert(
                        UserSecretsModel
                    )
                    .values(
                        **data.model_dump(mode="json")
                    )
                    .returning(
                        *self.user_secret_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while Creating user secret => {e}")
                return False
            

    async def update_user_secret(self,data:UpdateUserSecretDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    update(
                        UserSecretsModel
                    )
                    .where(
                        UserSecretsModel.id==data.id,
                        UserSecretsModel.user_id==data.user_id
                    )
                    .values(
                        **data.model_dump(mode="json",exclude=['id'],exclude_none=True,exclude_unset=True)
                    )
                    .returning(
                        *self.user_secret_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while Updating User secret => {e}")
                return False



    async def delete_user_secret(self,data:DeleteUserSecretDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    delete(
                        UserSecretsModel
                    )
                    .where(
                        UserSecretsModel.id==data.id,
                        UserSecretsModel.user_id==data.user_id
                    )
                    .returning(*self.user_secret_cols)
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erro while deleting user secretes => {e}")
                return False



    async def get_user_secret(self,data:GetUserSecretDbSchema)-> List[dict] | list:
        async with self.session.begin():
            try:
                cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
                stmt=(
                    select(
                        *self.user_secret_cols
                    )
                    .offset(offset=cursor)
                    .limit(limit=data.limit)
                )

                res=(await self.session.execute(stmt)).mappings().all()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erorr while getting user secret=> {e}")
                return False

            
    async def get_user_secret_by_id(self,data:GetUserSecretByIdSchema) -> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    select(
                        *self.user_secret_cols
                    )
                    .where(
                        UserSecretsModel.id==data.id

                    )  
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res

            except Exception as e:
                ic(f"Erorr while geting user secret by id => {e}")
                return False

            
    
    async def get_user_secret_by_user(self,data:GetUserSecretByUserSchema)-> List[dict] | list:
        async with self.session.begin():
            try:
                cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
                stmt=(
                    select(
                        *self.user_secret_cols
                    )
                    .where(
                        UserSecretsModel.user_id==data.user_id
                    )
                    .offset(offset=cursor)
                    .limit(limit=data.limit)
                )

                res=(await self.session.execute(stmt)).mappings().all()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while geting user secret by user => {e}")

