from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import secrets
import time,os
from hashlib import sha256
from core.security.jwt_token import generate_jwt_token
from loguru import logger
from operations.mongo_operations.users_crud import get_user_by_email
from operations.mongo_operations.end_users_crud import get_end_user_by_email as get_sso_user, create_end_user as create_sso_user, update_end_user

from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink,redis_curttl
from operations.redis_operations.session_manager import create_global_session, create_product_session, get_global_session
from schemas.db_schemas.end_user_schema import EndUser
from operations.mongo_operations.analytics_crud import log_audit_event, log_auth_request
import asyncio
from urllib.parse import urlparse, urlunparse

def get_client_ip(request) -> str:
    """
    Extracts the true client IP from standard proxy headers (X-Forwarded-For, X-Real-IP)
    or directly from the request connection.
    """
    if not request:
        return "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        for ip in ips:
            if ip.lower() not in ("127.0.0.1", "::1", "localhost", "unknown"):
                return ip
        if ips:
            return ips[0]
    real_ip = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    if getattr(request, "client", None) and request.client.host:
        return request.client.host
    return "127.0.0.1"


def sanitize_redirect_url(url: str, default: str = "/") -> str:
    if not url:
        return default
    cleaned = str(url).strip()
    if not cleaned:
        return default
    if cleaned.startswith(("http://", "https://", "/")):
        return cleaned
    lowered = cleaned.lower()
    if lowered.startswith(("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1")):
        return f"http://{cleaned}"
    if "." in cleaned and not cleaned.startswith("/"):
        return f"https://{cleaned}"
    return cleaned


def is_localhost_url(url: str) -> bool:
    if not url:
        return False
    try:
        cleaned = sanitize_redirect_url(url)
        parsed = urlparse(cleaned)
        hostname = (parsed.hostname or "").lower()
        return hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]")
    except Exception:
        return False


def resolve_target_url(url: str, client_ip: str = None) -> str:
    """
    Sanitizes and normalizes target verification/redirect URLs.
    Preserves loopback URLs (localhost/127.0.0.1) without rewriting to external WAN IPs.
    """
    if not url:
        return url
    return sanitize_redirect_url(url)


async def generate_redirect_code(auth_user:dict,auth_id:str,isfor_otp:bool=False, request=None, return_json:bool=False):
    session_data = await redis_get(auth_id) or {}
    
    extracted_auth_dict=auth_user
    if not isfor_otp:
        extracted_auth_dict=session_data

    await redis_unlink(auth_id)
    logger.debug(f"Extracted auth dict: {extracted_auth_dict}")
    suffix_token=secrets.token_urlsafe(10)
    
    config = extracted_auth_dict.get('config', {})
    user_email = config.get('user_email')
    user_data = await get_user_by_email(user_email) if user_email else None
    secret:dict = user_data.get('secrets',{}) if user_data else {}
    
    api_key = extracted_auth_dict.get('client_id') or extracted_auth_dict.get('apikey')
    client_secret:str = secret.get(api_key, None) if api_key else None

    if not client_secret:
        raise HTTPException(
            status_code=403,
            detail="client secret not found"
        )
    
    auth_code=sha256(client_secret.encode()).hexdigest()[:10]+suffix_token
    logger.debug(f"Generated auth_code: {auth_code}")

    locked_email = session_data.get('locked_email')
    locked_phone = session_data.get('locked_phone')
    lock_method = session_data.get('lock_method')
    prefilled = bool(locked_email or locked_phone)

    flow_type = (
        auth_user.get('flow_type') 
        or extracted_auth_dict.get('flow_type') 
        or session_data.get('flow_type') 
        or 'signin'
    )

    jwt_payload = {
        "email": auth_user.get('email') or None,
        "mobile_number": auth_user.get('mobile_number'),
        "name": auth_user.get('name') or auth_user.get('full_name'),
        'profile_picture': auth_user.get('profile_picture'),
        'flow_type': flow_type,
        'auth_provider': auth_user.get('auth_provider', 'unknown'),
        'custom_fields': auth_user.get('custom_fields', {}),
        'additional_infos': session_data.get('additional_infos'),
        'prefilled': prefilled,
        'lock_method': lock_method or None,
        'location': {
            'lat': session_data.get('latitude'),
            'lng': session_data.get('longitude')
        } if session_data.get('latitude') is not None else None
    }

    if request:
        jwt_payload['ip'] = get_client_ip(request)
        jwt_payload['browser'] = request.headers.get("User-Agent", "unknown")

    ip_addr = get_client_ip(request) if request else "unknown"
    asyncio.create_task(log_audit_event(
        api_key,
        ip_addr,
        auth_user.get('auth_provider', 'unknown'),
        auth_user.get('email') or auth_user.get('mobile_number') or "unknown",
        "LOGIN_SUCCESS",
        "SUCCESS"
    ))
    asyncio.create_task(log_auth_request(
        api_key,
        auth_user.get('auth_provider', 'unknown')
    ))

    if auth_user.get('auth_provider') in ['password', 'forgot-password'] and 'password' in auth_user:
        jwt_payload['password'] = auth_user['password']

    app_token = generate_jwt_token(jwt_payload, exp_min=60)

    authenticated_values={
        'token':app_token,
        'suffix_token':suffix_token,
        'user_email':user_email,
        'apikey':api_key
    }
    await redis_set(key=auth_code,value=authenticated_values,exp=300)

    redirect_urls = config.get('redirect_urls', {})
    
    if flow_type == 'signup':
        raw_url = redirect_urls.get('signup_success') or config.get('redirect_url', '/')
    else:
        raw_url = redirect_urls.get('signin_success') or config.get('redirect_url', '/')

    deb_apikey = os.getenv("DEB_APIKEY", "")
    if api_key == deb_apikey and (not raw_url or raw_url == '/'):
        default_base = os.getenv("REDIRECT_BASEURL", "http://127.0.0.1:8000")
        raw_url = f"{default_base}/user/create"
        
    base_url = sanitize_redirect_url(raw_url)
    separator = "&" if "?" in base_url else "?"
    redirect_url_final = f"{base_url}{separator}token_id={auth_code}"
    
    if return_json:
        response = JSONResponse(content={"redirect_url": redirect_url_final})
    else:
        response = RedirectResponse(url=redirect_url_final, status_code=302)
    
    # SSO Logic
    sso_config = config.get('sso', {})
    if sso_config.get('enabled', False) and request:
        product_id = api_key
        user_email_sso = auth_user.get('email')
        
        # Check if EndUser exists, if not create
        sso_user = await get_sso_user(product_id, user_email_sso)
        if not sso_user:
            sso_user = EndUser(
                id=secrets.token_hex(16),
                email=user_email,
                mobile_number=auth_user.get('mobile_number'),
                name=auth_user.get('name') or auth_user.get('full_name'),
                profile_picture=auth_user.get('profile_picture'),
                created_at=time.time(),
                custom_fields=auth_user.get('custom_fields', {})
            )
            await create_sso_user(product_id, sso_user)
            
        # Determine best cookie domain for cross-subdomain SSO sharing
        client_origin = request.headers.get("origin") or request.headers.get("referer") or ""
        from urllib.parse import urlparse
        parsed = urlparse(client_origin)
        caller_host = parsed.netloc.lower()
        if ":" in caller_host:
            caller_host = caller_host.split(":")[0]

        cookie_domain = None
        registered_domains = sso_config.get('domains', [])
        for domain in registered_domains:
            d_str = (domain.get("domain") if isinstance(domain, dict) else str(domain)).strip().lower()
            if not d_str:
                continue
            # Check matches
            matched = False
            if caller_host == d_str:
                matched = True
            elif d_str.startswith("*.") and caller_host.endswith(d_str[2:]):
                matched = True
                cookie_domain = f".{d_str[2:]}" # enable sharing across subdomains
            elif d_str.startswith("*") and d_str.endswith("*") and d_str[1:-1] in caller_host:
                matched = True
            elif d_str.startswith("*") and caller_host.endswith(d_str[1:]):
                matched = True
            elif d_str.endswith("*") and caller_host.startswith(d_str[:-1]):
                matched = True

            if matched:
                # Update accessed sites in user fields
                if 'signed_in_sites' not in sso_user.custom_fields:
                    sso_user.custom_fields['signed_in_sites'] = []
                site_info = {"url": client_origin or caller_host, "timestamp": time.time()}
                if site_info["url"] not in [s.get("url") for s in sso_user.custom_fields['signed_in_sites'] if isinstance(s, dict)]:
                    sso_user.custom_fields['signed_in_sites'].append(site_info)
                await update_end_user(product_id, sso_user)
                break

        global_session_id = request.cookies.get("global_session_id")
        ip = request.client.host if request.client else "unknown"
        device = request.headers.get("User-Agent", "unknown")
        
        if not global_session_id or not await get_global_session(global_session_id):
            session = await create_global_session(sso_user.id, ip, device)
            global_session_id = session.session_id
            response.set_cookie(
                key="global_session_id", 
                value=global_session_id, 
                httponly=True, 
                samesite="lax", 
                secure=True,
                domain=cookie_domain
            )
            
        await create_product_session(global_session_id, product_id, sso_user.id)


    return response