from ..models.ui_model import UserInterfacesModel
from schemas.request_schemas.auth_schema import *
from schemas.request_schemas.redirect_schema import CreateRedirectSchema,BaseRedirectSchema
from schemas.request_schemas.user_client_schema import UserClientDeviceInfos
from typing import Optional,List
from icecream import ic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update,delete,select,or_,and_


class UserClientRepo:
    async def __init__(self,session:AsyncSession):
        self.session=session
    
