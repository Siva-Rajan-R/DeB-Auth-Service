from schemas.request_schemas.auth_schema import *
from schemas.request_schemas.redirect_schema import CreateRedirectSchema,BaseRedirectSchema
from schemas.request_schemas.ui_schema import CreateUiSchema,UpdateUiSchema,DeleteUiSchema,GetByIdUiSchema,GetByUserUiSchema,GetUiSchema
from schemas.request_schemas.user_client_schema import UserClientDeviceInfos
from typing import Optional,List
from icecream import ic
from sqlalchemy.ext.asyncio import AsyncSession
from infras.primary_db.repos.ui_repo import UserInterfaceRepo
from infras.primary_db.repos.user_client_repo import UserClientRepo
from infras.primary_db.repos.user_repo import UserRepo


from infras.primary_db.services.ui_service import UserInterfaceService
from infras.primary_db.services.user_client_service import UserClientService
from infras.primary_db.services.user_service import UserService


class UserInterfaceHandler:
    async def __init__(self,session:AsyncSession):
        self.session=session
        self.ui_service_obj=UserInterfaceService(session=session)

    async def create(self,data:CreateUiSchema)-> dict:
        res=await self.ui_service_obj.create(data=data)
        ic(res)
        return res

    
    async def update(self,data:UpdateUiSchema):
        res=await self.ui_service_obj.update(data=data)
        ic(res)
        return res

    
    async def delete(self,data:DeleteUiSchema):
        res=await self.ui_service_obj.delete(data=data)
        ic(res)
        return res


    async def get(self,data:GetUiSchema):
        res=await self.ui_service_obj.get(data=data)
        ic(res)
        return res

    

    async def getby_id(self,data:GetByIdUiSchema):
        res=await self.ui_service_obj.getby_id(data=data)
        ic(res)
        return res


    async def getby_user(self,data:GetByUserUiSchema):
        res=await self.ui_service_obj.getby_user(data=data)
        ic(res)
        return res


