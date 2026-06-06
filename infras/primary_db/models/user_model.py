from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Integer,Float,TIMESTAMP,func,Boolean,ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from ..main import AsyncSession,BASE
from datetime import date,datetime
from typing import Optional,List
from schemas.request_schemas.fields_schema import BaseFieldsSchema



class UsersModel(BASE):
    __tablename__="users"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    name:Mapped[str]=mapped_column(String,nullable=False)
    email:Mapped[str]=mapped_column(String,unique=True,nullable=False)
    mobile_number:Mapped[str]=mapped_column(String,nullable=True)


    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())



class UserSecretsModel(BASE):
    __tablename__="user_secrets"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    user_id:Mapped[str]=mapped_column(String,nullable=False)
    client_id:Mapped[str]=mapped_column(String,nullable=False)
    client_secret:Mapped[str]=mapped_column(String,nullable=False)

    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())


class UserSettingsModel(BASE):
    __tablename__="user_settings"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    user_id:Mapped[str]=mapped_column(String,nullable=False)
    client_id:Mapped[str]=mapped_column(String,nullable=False)
    sso_enabled:Mapped[bool]=mapped_column(Boolean,nullable=True,server_default=False)


    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())


class UserRedirectModel(BASE):
    __tablename__="user_redirect"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    client_id:Mapped[str]=mapped_column(String,nullable=False)
    user_id:Mapped[str]=mapped_column(String,nullable=False)
    sign_in:Mapped[dict]=mapped_column(JSONB,nullable=False)
    sign_up:Mapped[dict]=mapped_column(JSONB,nullable=False)


    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())


class UserSignupFieldsModel(BASE):
    __tablename__="user_signup_fields"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    client_id:Mapped[str]=mapped_column(String,nullable=False)
    fields:Mapped[List[BaseFieldsSchema]]=mapped_column(JSONB,nullable=False)
    user_id:Mapped[str]=mapped_column(String,nullable=False)
    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())


class UserDropDownsModel(BASE):
    id:Mapped[str]=mapped_column(String,primary_key=True)
    client_id:Mapped[str]=mapped_column(String,nullable=False)
    roles:Mapped[List[str]]=mapped_column(ARRAY(String),nullable=True)
    user_id:Mapped[str]=mapped_column(String,nullable=False)
    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())






