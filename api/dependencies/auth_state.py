from fastapi import Request, HTTPException, Header
from typing import Optional
from schemas.auth_state_schema import AuthState, DeviceFingerprint
from operations.redis_operations.handlers import redis_get, redis_set
from icecream import ic
import time

AUTH_TIMEOUT_SECONDS = 300 # 5 minutes

async def get_and_validate_auth_state(
    request: Request,
    request_id: str,
    required_step: Optional[str] = None,
    allow_pending: bool = False
) -> AuthState:
    auth_values = await redis_get(key=request_id)
    if not auth_values:
        raise HTTPException(status_code=404, detail="Invalid or expired request ID")
    
    state = AuthState(**auth_values)
    
    failure_url = state.config.get('redirect_urls', {}).get('signin_failure', '/')

    # 1. Validate Status
    if state.status == "completed":
        raise HTTPException(status_code=403, detail={"message": "Authentication flow already completed", "redirect_url": failure_url})
    if state.status in ["failed", "cancelled", "expired"]:
        raise HTTPException(status_code=403, detail={"message": f"Authentication flow is {state.status}", "redirect_url": failure_url})
    if state.status == "pending" and not allow_pending:
        raise HTTPException(status_code=403, detail={"message": "Authentication flow not initialized", "redirect_url": failure_url})

    # 2. Validate Timeout
    current_time = time.time()
    if current_time - state.last_activity > AUTH_TIMEOUT_SECONDS:
        state.status = "expired"
        await redis_set(key=request_id, value=state.model_dump(), exp=60)
        raise HTTPException(status_code=403, detail={"message": "Authentication flow timed out", "redirect_url": failure_url})
    
    # 3. Validate Fingerprint (if initialized)
    ip = request.client.host if request.client else "unknown"
    browser = request.headers.get("x-device-browser")
    os = request.headers.get("x-device-os")
    device = request.headers.get("x-device-type")
    user_agent = request.headers.get("user-agent")

    current_fingerprint = DeviceFingerprint(
        ip=ip, browser=browser, os=os, device=device, user_agent=user_agent
    )

    if state.device_fingerprint:
        stored = state.device_fingerprint
        if stored.ip != current_fingerprint.ip:
            state.status = "failed"
            await redis_set(key=request_id, value=state.model_dump(), exp=60)
            raise HTTPException(status_code=403, detail={"message": "FINGERPRINT_MISMATCH: IP Address changed", "redirect_url": failure_url})
        
        # We can also strictly check browser/os if we want, but user agents can sometimes slightly shift.
        # Strict exact match as requested:
        if stored.browser and stored.browser != current_fingerprint.browser:
            state.status = "failed"
            await redis_set(key=request_id, value=state.model_dump(), exp=60)
            raise HTTPException(status_code=403, detail={"message": "FINGERPRINT_MISMATCH: Browser changed", "redirect_url": failure_url})
            
        if stored.os and stored.os != current_fingerprint.os:
            state.status = "failed"
            await redis_set(key=request_id, value=state.model_dump(), exp=60)
            raise HTTPException(status_code=403, detail={"message": "FINGERPRINT_MISMATCH: Operating System changed", "redirect_url": failure_url})

    # 4. Validate Step Order
    if required_step and required_step not in state.completed_steps:
        raise HTTPException(
            status_code=403, 
            detail={"message": f"INVALID_AUTH_FLOW: Required previous step '{required_step}' not completed.", "redirect_url": failure_url}
        )

    # Update activity timestamp
    state.last_activity = current_time
    await redis_set(key=request_id, value=state.model_dump(), exp=AUTH_TIMEOUT_SECONDS)

    return state

