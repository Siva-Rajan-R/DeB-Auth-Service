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


class UserSignupFieldRepo:
    def __init__(self,session:AsyncSession):
        self.session=session
        self.user_signup_fields_cols=(
            UserSignupFieldsModel.id,
            UserSignupFieldsModel.user_id,
            UserSignupFieldsModel.fields,
            UserSignupFieldsModel.created_at,
            UserSignupFieldsModel.updated_at
        )



    async def create_user_signup_field(self,data:CreateUserSignupFieldsSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    insert(
                        UserSignupFieldsModel
                    )
                    .values(
                        **data.model_dump(mode="json")
                    )
                    .returning(
                        *self.user_signup_fields_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while Creating user Redirect => {e}")
                return False




    async def update_user_signup_field(self,data:UpdateUserSignupFieldDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    update(
                        UserSignupFieldsModel
                    )
                    .where(
                        UserSignupFieldsModel.id==data.id,
                        UserSignupFieldsModel.user_id==data.user_id
                    )
                    .values(
                        **data.model_dump(mode="json",exclude=['id'],exclude_none=True,exclude_unset=True)
                    )
                    .returning(
                        *self.user_signup_fields_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while Updating User signup fields => {e}")
                return False




    async def delete_user_signup_field(self,data:DeleteUserSignUpFieldsDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    delete(
                        UserSignupFieldsModel
                    )
                    .where(
                        UserSignupFieldsModel.id==data.id,
                        UserSignupFieldsModel.user_id==data.user_id
                    )
                    .returning(*self.user_signup_fields_cols)
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erro while deleting usersignup fields => {e}")
                return False



    async def get_user_signup_field(self,data:GetUserSignUpFieldsDbSchema)-> List[dict] | list:
        async with self.session.begin():
            try:
                cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
                stmt=(
                    select(
                        *self.user_signup_fields_cols
                    )
                    .offset(offset=cursor)
                    .limit(limit=data.limit)
                )

                res=(await self.session.execute(stmt)).mappings().all()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erorr while getting usersignup field => {e}")
                return False


            

    async def get_user_signup_field_by_id(self,data:GetUserSignUpFielsByIdDbSchema) -> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    select(
                        *self.user_signup_fields_cols
                    )
                    .where(
                        UserSignupFieldsModel.id==data.id,
                        UserSignupFieldsModel.user_id==data.user_id
                    )  
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res

            except Exception as e:
                ic(f"Erorr while geting user signup field by id => {e}")
                return False
            


    async def get_user_signup_field_by_user(self,data:GetUserSignUpFielsByUserDbSchema)-> List[dict] | list:
        async with self.session.begin():
            try:
                cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
                stmt=(
                    select(
                        *self.user_signup_fields_cols
                    )
                    .where(
                        UserSignupFieldsModel.user_id==data.user_id
                    )
                    .offset(offset=cursor)
                    .limit(limit=data.limit)
                )

                res=(await self.session.execute(stmt)).mappings().all()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while geting user sign-up by user => {e}")



