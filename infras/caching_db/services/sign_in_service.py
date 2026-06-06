from ..main import redis_set,redis_get,redis_unlink
from pydantic import BaseModel
from typing import List

class SetLoginInfoSchema(BaseModel):
    link_id:str
    client_id:str
    client_secret:str


class SignInCacheService:
    @staticmethod
    async def set_login_info(data:SetLoginInfoSchema):
        return await redis_set(key=data.link_id,value=data.model_dump(mode="json"),exp=10000)

    @staticmethod
    async def get_login_info(link_id: str):
        return await redis_get(key=link_id)
    
    @staticmethod
    async def unlink_login_info(link_ids: List[str]):
        return await redis_unlink(keys=link_ids)