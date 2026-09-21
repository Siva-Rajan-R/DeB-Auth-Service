import httpx
from fastapi import HTTPException
from urllib.parse import quote
from loguru import logger
from utils.redirectcode_genereator import sanitize_redirect_url
import asyncio
from operations.mongo_operations.analytics_crud import log_audit_event


async def perform_external_verification(
    verification_url: str,
    failure_url: str,
    payload: dict,
    request,
    client_id: str,
    auth_provider: str,
    identifier: str,
    current_attempts: int = 1,
    max_attempts: int = 3
) -> dict:
    """
    Calls an external verification / checking webhook URL configured by the client.
    
    If the endpoint returns 2xx and no failure indicator:
        Returns the parsed JSON response.
    If the endpoint returns non-2xx or indicates failure:
        If current_attempts < max_attempts:
            Raises HTTPException without redirect_url so the user can see the error and retry in the UI.
        If current_attempts >= max_attempts:
            Builds the failure_redirect URL with error params, logs the audit failure,
            and raises an HTTPException with redirect_url to callback to the failure URL.
    """
    if not verification_url:
        return {}

    cleaned_url = sanitize_redirect_url(verification_url)
    if not cleaned_url or cleaned_url == "/":
        return {}

    logger.info(f"Calling verification endpoint: {cleaned_url} for client: {client_id} (Attempt {current_attempts}/{max_attempts})")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                cleaned_url,
                json=payload,
                headers={
                    "x-dauth-request-id": str(payload.get("request_id", "")),
                    "x-client-id": str(client_id or ""),
                    "Content-Type": "application/json",
                    "User-Agent": "DAuth-Verification-Service/1.0"
                }
            )

            resp_json = {}
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = {"detail": resp.text}

            # Check for failure status code or explicit failure keys
            is_success = (
                (resp.status_code >= 200 and resp.status_code < 300)
                and resp_json.get("success") is not False
                and resp_json.get("status") not in ["error", "failed", "failure"]
            )

            if not is_success:
                status_code = resp.status_code if (400 <= resp.status_code < 600) else (
                    resp_json.get("status_code") or resp_json.get("code") or 401
                )
                raw_msg = (
                    resp_json.get("msg")
                    or resp_json.get("message")
                    or resp_json.get("detail")
                    or resp_json.get("error")
                    or f"Verification failed with status code {resp.status_code}"
                )
                if isinstance(raw_msg, dict):
                    raw_msg = raw_msg.get("message") or raw_msg.get("msg") or str(raw_msg)

                msg = str(raw_msg)

                ip = request.client.host if request and request.client else "unknown"
                asyncio.create_task(
                    log_audit_event(client_id, ip, auth_provider, identifier, "VERIFICATION_FAILED", "FAILED")
                )

                if current_attempts < max_attempts:
                    remaining = max_attempts - current_attempts
                    attempt_text = f"{remaining} attempt{'s' if remaining > 1 else ''} remaining"
                    display_msg = f"{msg} ({attempt_text})"
                    raise HTTPException(
                        status_code=status_code if (isinstance(status_code, int) and 400 <= status_code < 600) else 401,
                        detail={
                            "message": display_msg,
                            "raw_message": msg,
                            "status_code": status_code,
                            "attempts_remaining": remaining
                        }
                    )
                else:
                    failure_redirect = None
                    if failure_url:
                        base_fail = sanitize_redirect_url(failure_url)
                        sep = "&" if "?" in base_fail else "?"
                        failure_redirect = f"{base_fail}{sep}error={quote(str(msg))}&status_code={status_code}"

                    raise HTTPException(
                        status_code=status_code if (isinstance(status_code, int) and 400 <= status_code < 600) else 401,
                        detail={
                            "message": f"{msg}. Maximum attempts reached.",
                            "status_code": status_code,
                            "redirect_url": failure_redirect,
                            "attempts_remaining": 0
                        }
                    )

            return resp_json if isinstance(resp_json, dict) else {}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calling verification URL ({cleaned_url}): {e}")
        status_code = 502
        msg = f"Failed to reach verification endpoint: {str(e)}"
        
        ip = request.client.host if request and request.client else "unknown"
        asyncio.create_task(
            log_audit_event(client_id, ip, auth_provider, identifier, "VERIFICATION_ERROR", "FAILED")
        )

        if current_attempts < max_attempts:
            remaining = max_attempts - current_attempts
            raise HTTPException(
                status_code=502,
                detail={
                    "message": f"{msg} ({remaining} attempts remaining)",
                    "status_code": 502,
                    "attempts_remaining": remaining
                }
            )
        else:
            failure_redirect = None
            if failure_url:
                base_fail = sanitize_redirect_url(failure_url)
                sep = "&" if "?" in base_fail else "?"
                failure_redirect = f"{base_fail}{sep}error={quote(str(msg))}&status_code={status_code}"

            raise HTTPException(
                status_code=502,
                detail={
                    "message": f"{msg} Maximum attempts reached.",
                    "status_code": 502,
                    "redirect_url": failure_redirect,
                    "attempts_remaining": 0
                }
            )
