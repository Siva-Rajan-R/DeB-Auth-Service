from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class DeviceFingerprint(BaseModel):
    ip: str
    browser: Optional[str] = None
    os: Optional[str] = None
    device: Optional[str] = None
    user_agent: Optional[str] = None

class AuthState(BaseModel):
    request_id: str
    client_id: str
    config: Dict[str, Any]
    flow_type: Optional[str] = None # 'signin' or 'signup'
    status: str = "pending" # pending, active, completed, failed, expired, cancelled
    device_fingerprint: Optional[DeviceFingerprint] = None
    current_step: str = "request_validation"
    completed_steps: List[str] = ["request_validation"]
    last_activity: float
    auth_data: Dict[str, Any] = {}
    # If set, only this email is allowed for all subsequent auth steps in this session.
    # Set via ?prefill_email=... during flow init and enforced server-side.
    locked_email: Optional[str] = None
