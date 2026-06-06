from pydantic import BaseModel
from typing import Optional,List,Dict
from core.data_formats.enums.provider_enum import ProvidersEnum



class UserClientDeviceInfos(BaseModel):
    device_name:str
    ip:str
