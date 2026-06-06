from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Integer,Float,TIMESTAMP,func
from sqlalchemy.dialects.postgresql import JSONB
from ..main import AsyncSession,BASE
from datetime import date,datetime


class UserInterfacesModel(BASE):
    __tablename__="user_interfaces"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    client_id:Mapped[str]=mapped_column(String,nullable=False)
    user_id:Mapped[str]=mapped_column(String,nullable=False)
    branding:Mapped[dict]=mapped_column(JSONB,nullable=False)
    styling:Mapped[dict]=mapped_column(JSONB,nullable=True)


    created_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now())
    updated_at=Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True),server_default=func.now(),onupdate=func.now())
