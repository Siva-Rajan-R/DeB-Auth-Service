from schemas.request_schemas.auth_schema import *
from schemas.request_schemas.redirect_schema import CreateRedirectSchema,BaseRedirectSchema
from schemas.request_schemas.ui_schema import CreateUiSchema,UpdateUiSchema
from schemas.request_schemas.user_client_schema import UserClientDeviceInfos
from typing import Optional,List
from icecream import ic

from infras.primary_db.repos.ui_repo import UserInterfaceRepo
from infras.primary_db.repos.user_client_repo import UserClientRepo
from infras.primary_db.repos.user_repo import UserRepo


from infras.primary_db.services.ui_service import UserInterfaceService
from infras.primary_db.services.user_client_service import UserClientService
from infras.primary_db.services.user_service import UserService



class UserHandler:
    ...