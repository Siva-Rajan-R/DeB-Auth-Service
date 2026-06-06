from typing import Optional,List
from pydantic import BaseModel
from infras.primary_db.main import AsyncSession
from ..services.otp_service import OtpService
from schemas.request_schemas.sign_in_schema import CreateLinkSchema,AuthenticateSchema,GetUiInfoSchema
from ..repos.user_secret_repo import UserSecretRepo,GetUserSecretByIdSchema
from ..repos.ui_repo import UserInterfaceRepo
from icecream import ic
from ...caching_db.services.sign_in_service import SignInCacheService,SetLoginInfoSchema
from core.utils.uuid_generator import generate_uuid

FRONTEND_URL=""

class SignInService:
    def __init__(self,session:AsyncSession):
        self.session=session

    

    async def create_link(self,data:CreateLinkSchema):
        is_exists=await UserSecretRepo(session=self.session).get_user_secret_by_id(data=GetUserSecretByIdSchema(id=data.client_id))
        if not is_exists:
            ic("Client_id not exists")
            return False
        
        link_id:str=generate_uuid()
        client_id:str=data.client_id
        client_secret:str=is_exists['client_secret']

        cache_res=await SignInCacheService.set_login_info(data=SetLoginInfoSchema(link_id=link_id,client_secret=client_secret,client_id=client_id))
        ic(cache_res)
        
        sign_in_url=f"{FRONTEND_URL}/{link_id}"
        ic(sign_in_url)
        return sign_in_url
    

    async def get_ui_infos(self,data:GetUiInfoSchema):
        caches_res=await SignInCacheService.get_login_info(link_id=data.link_id)
        ic(caches_res)
        if not caches_res:
            ic("Session expired cache-data not fount")
            return False
        
        ui
    

    async def authenticate(self,data:AuthenticateSchema):
        data
    



        
