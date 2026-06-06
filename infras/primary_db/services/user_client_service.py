from ..models.ui_model import UserInterfacesModel
from schemas.request_schemas.auth_schema import *
from schemas.request_schemas.redirect_schema import CreateRedirectSchema,BaseRedirectSchema
from schemas.request_schemas.ui_schema import CreateUiSchema,UpdateUiSchema
from schemas.request_schemas.user_client_schema import UserClientDeviceInfos
from typing import Optional,List
from icecream import ic
from ..repos.ui_repo import UserInterfaceRepo
from ..repos.user_client_repo import UserClientRepo
from ..repos.user_repo import UserRepo


class UserClientService:
    ...