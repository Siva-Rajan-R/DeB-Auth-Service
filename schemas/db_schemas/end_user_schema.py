from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any

class EndUser(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    roles: List[str] = []
    created_at: float
    last_login: Optional[float] = None
    custom_fields: Dict[str, Any] = {}

class GlobalSession(BaseModel):
    session_id: str
    user_id: str
    created_at: float
    last_activity: float
    expires_at: float
    device_info: str
    ip_info: str

class ProductSession(BaseModel):
    session_id: str
    global_session_id: str
    product_id: str # apikey
    user_id: str
    created_at: float
    expires_at: float
    status: str = "active"

class Role(BaseModel):
    role_id: str
    name: str
    permissions: List[str]
