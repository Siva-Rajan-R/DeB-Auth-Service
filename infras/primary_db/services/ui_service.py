from ..models.ui_model import UserInterfacesModel
from schemas.request_schemas.auth_schema import *
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.request_schemas.redirect_schema import CreateRedirectSchema,BaseRedirectSchema
from schemas.request_schemas.ui_schema import CreateUiSchema,UpdateUiSchema,DeleteUiSchema,GetByIdUiSchema,GetByUserUiSchema,GetUiSchema
from schemas.db_schemas.ui_schema import CreateUiDbSchema,UpdateUiDbSchema
from schemas.request_schemas.user_client_schema import UserClientDeviceInfos
from typing import Optional,List
from icecream import ic
from ..repos.ui_repo import UserInterfaceRepo
from ..repos.user_client_repo import UserClientRepo
from ..repos.user_repo import UserRepo
from core.security.unique_id import generate_unique_id


class UserInterfaceService:
    async def __init__(self,session:AsyncSession):
        self.session=session
        self.ui_repo_obj=UserInterfaceRepo(session=session)

    async def create(self,data:CreateUiSchema)-> dict | None:
        data_toadd=CreateUiDbSchema(
            **data.model_dump(mode="json"),
            id=generate_unique_id()
        )

        res=await self.ui_repo_obj.create(data=data_toadd)
        ic(res)
        return res

    
    async def update(self,data:UpdateUiSchema) -> dict | None:
        data_toupdate=UpdateUiDbSchema(
            **data.model_dump(mode="json"),
            id=generate_unique_id()
        )

        res=await self.ui_repo_obj.update(data=data_toupdate)
        ic(res)
        return res

    
    async def delete(self,data:DeleteUiSchema) -> dict | None:
        res=await self.ui_repo_obj.delete(data=data)
        ic(res)
        return res

    

    async def get(self,data:GetUiSchema) -> List[dict] | list:
        res=await self.ui_repo_obj.get(data=data)
        ic(res)
        return res

    

    async def getby_id(self,data:GetByIdUiSchema)-> dict | None:
        res=await self.ui_repo_obj.getby_id(data=data)
        ic(res)
        return res


    async def getby_user(self,data:GetByUserUiSchema)-> List[dict] | list:
        res=await self.ui_repo_obj.getby_user(data=data)
        ic(res)
        return res