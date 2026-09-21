from pydantic import BaseModel
from typing import Optional


class BaseRedirectSchema(BaseModel):
    success_redirect_url: str
    failure_redirect_url: str
    verification_url: Optional[str] = None


class CreateRedirectSchema(BaseModel):
    sign_in: BaseRedirectSchema
    sign_up: BaseRedirectSchema
