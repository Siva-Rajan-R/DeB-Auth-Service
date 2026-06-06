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


class UserSettingRepo:
    def __init__(self,session:AsyncSession):
        self.session=session
        self.user_setting_cols=(
            UserSettingsModel.id,
            UserSettingsModel.user_id,
            UserSettingsModel.sso_enabled,
            UserSettingsModel.created_at,
            UserSettingsModel.updated_at
        )

            


    async def create_user_setting(self,data:CreateUserSettingDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    insert(
                        UserSettingsModel
                    )
                    .values(
                        **data.model_dump(mode="json")
                    )
                    .returning(
                        *self.user_setting_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while Creating user setting => {e}")
                return False




    async def update_user_setting(self,data:UpdateUserSettingDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    update(
                        UserSettingsModel
                    )
                    .where(
                        UserSettingsModel.id==data.id,
                        UserSettingsModel.user_id==data.user_id
                    )
                    .values(
                        **data.model_dump(mode="json",exclude=['id'],exclude_none=True,exclude_unset=True)
                    )
                    .returning(
                        *self.user_setting_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while Updating User setting => {e}")
                return False



    async def delete_user_setting(self,data:DeleteUserSettingDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    delete(
                        UserSettingsModel
                    )
                    .where(
                        UserSettingsModel.id==data.id,
                        UserSettingsModel.user_id==data.user_id
                    )
                    .returning(*self.user_setting_cols)
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erro while deleting user setting => {e}")
                return False



    async def get_user_setting(self,data:GetUserSettingDbSchema)-> List[dict] | list:
        async with self.session.begin():
            try:
                cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
                stmt=(
                    select(
                        *self.user_setting_cols
                    )
                    .offset(offset=cursor)
                    .limit(limit=data.limit)
                )

                res=(await self.session.execute(stmt)).mappings().all()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erorr while getting user setting=> {e}")
                return False

            
    async def get_user_setting_by_id(self,data:GetuserSettingByIdDbSchema) -> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    select(
                        *self.user_setting_cols
                    )
                    .where(
                        UserSettingsModel.id==data.id,
                        UserSettingsModel.user_id==data.user_id
                    )  
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none()
                ic(res)
                return res

            except Exception as e:
                ic(f"Erorr while geting user setting by id => {e}")
                return False



    async def get_user_setting_by_user(self,data:GetUserSettingByUserDbSchema)-> List[dict] | list:
        async with self.session.begin():
            try:
                cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
                stmt=(
                    select(
                        *self.user_setting_cols
                    )
                    .where(
                        UserSettingsModel.user_id==data.user_id
                    )
                    .offset(offset=cursor)
                    .limit(limit=data.limit)
                )

                res=(await self.session.execute(stmt)).mappings().all()
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while geting user setting by user => {e}")



