from ..models.ui_model import UserInterfacesModel
from sqlalchemy import select,update,delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.request_schemas.redirect_schema import CreateRedirectSchema,BaseRedirectSchema
from schemas.request_schemas.ui_schema import CreateUiSchema,UpdateUiSchema,DeleteUiSchema,GetByIdUiSchema,GetByUserUiSchema,GetUiSchema
from schemas.db_schemas.ui_schema import CreateUiDbSchema,UpdateUiDbSchema
from schemas.request_schemas.user_client_schema import UserClientDeviceInfos
from typing import Optional,List
from icecream import ic


class UserInterfaceRepo:
    async def __init__(self,session:AsyncSession):
        self.session=session
        self.ui_cols=(
            UserInterfacesModel.id,
            UserInterfacesModel.branding,
            UserInterfacesModel.styling,
            UserInterfacesModel.created_at
        )
    async def create(self,data:CreateUiDbSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    insert(
                        UserInterfacesModel
                    )
                    .values(
                        **data.model_dump(mode='json')
                    )
                    .returning(*self.ui_cols)
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error while creating user-interface => {e}")

    
    async def update(self,data:UpdateUiDbSchema) -> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    update(
                        UserInterfacesModel
                    )
                    .where(
                        UserInterfacesModel.id==data.id,
                        UserInterfacesModel.user_id==data.user_id
                    )
                    .values(
                        **data.model_dump(mode="json",exclude=['id'],exclude_none=True,exclude_unset=True)
                    )
                    .returning(
                        *self.ui_cols
                    )
                )


                res=(await self.session.execute(stmt)).mappings().one_or_none
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Error updating User-interface => {e}")

    
    async def delete(self,data:DeleteUiSchema)-> dict | None:
        async with self.session.begin():
            try:
                stmt=(
                    delete(
                        UserInterfacesModel
                    )
                    .where(
                        UserInterfacesModel.id==data.id,
                        UserInterfacesModel.user_id==data.user_id
                    )
                    .returning(
                        *self.ui_cols
                    )
                )

                res=(await self.session.execute(stmt)).mappings().one_or_none
                ic(res)
                return res
            
            except Exception as e:
                ic(f"Erro while Deleting UserInterface => {e}")

    

    async def get(self,data:GetUiSchema)-> List[dict] | list:
        try:
            cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
            stmt=(
                select(
                    *self.ui_cols
                )
                .offset(offset=cursor)
                .limit(limit=data.limit)
            )

            res=(await self.session.execute(stmt)).mappings().all()
            ic(res)
            return res
        
        except Exception as e:
            ic(f"Error while getting user-interface -> {e}")

    

    async def getby_id(self,data:GetByIdUiSchema)-> dict | None:
        try:
            stmt=(
                select(
                    *self.ui_cols
                )
                .where(
                    UserInterfacesModel.id==data.id,
                    UserInterfacesModel.user_id==data.user_id
                )

            )

            res=(await self.session.execute(stmt)).mappings().one_or_none()
            ic(res)
            return res
        
        except Exception as e:
            ic(f"Error while getting-by-id user-interface -> {e}")


    async def getby_user(self,data:GetByUserUiSchema)-> List[dict] | list:
        try:
            cursor=(data.offset-1)*data.limit if data.offset>0 else data.offset
            stmt=(
                select(
                    *self.ui_cols
                )
                .where(
                    UserInterfacesModel.user_id==data.user_id
                )
                .offset(offset=cursor)
                .limit(limit=data.limit)
            )

            res=(await self.session.execute(stmt)).mappings().all()
            ic(res)
            return res
        
        except Exception as e:
            ic(f"Error while getting-by-id user-interface -> {e}")