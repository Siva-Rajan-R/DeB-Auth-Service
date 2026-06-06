from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Integer,Float,TIMESTAMP,func,Boolean
from sqlalchemy.dialects.postgresql import JSONB
from ..main import AsyncSession,BASE
from datetime import date,datetime
from typing import Optional,List
from schemas.request_schemas.user_client_schema import UserClientDeviceInfos



class UserClientsModel(BASE):
    __tablename__="user_clients"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    client_id:Mapped[str]=mapped_column(String,nullable=False)
    name:Mapped[str]=mapped_column(String,nullable=True)
    email:Mapped[str]=mapped_column(String,nullable=False)
    mobile_number:Mapped[str]=mapped_column(String,nullable=True)

    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())


class UserClientsRoleModel(BASE):
    id:Mapped[str]=mapped_column(String,primary_key=True)
    user_client_id:Mapped[str]=mapped_column(String,nullable=False)
    role:Mapped[str]=mapped_column(String,nullable=False)

    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())


class UserClientSessionsModel(BASE):
    id:Mapped[str]=mapped_column(String,primary_key=True)
    session_id:Mapped[str]=mapped_column(String,nullable=False,unique=True)
    device_info:Mapped[UserClientDeviceInfos]=mapped_column(JSONB,nullable=False)
    private_key:Mapped[String]=mapped_column(String,nullable=False)
    public_key:Mapped[String]=mapped_column(String,nullable=False)

    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())


