from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import secrets
import time
from hashlib import sha256
from core.security.jwt_token import generate_jwt_token
from icecream import ic
from operations.fb_operations.users_crud import get_user_by_email
from operations.fb_operations.end_users_crud import get_end_user_by_email as get_sso_user, create_end_user as create_sso_user, update_end_user

from operations.redis_operations.handlers import redis_set,redis_get,redis_unlink,redis_curttl
from operations.redis_operations.session_manager import create_global_session, create_product_session, get_global_session
from schemas.db_schemas.end_user_schema import EndUser

async def generate_redirect_code(auth_user:dict,auth_id:str,isfor_otp:bool=False, request=None, return_json:bool=False):
    session_data = await redis_get(auth_id) or {}
    
    extracted_auth_dict=auth_user
    if not isfor_otp:
        extracted_auth_dict=session_data

    await redis_unlink(auth_id)
    ic(extracted_auth_dict)
    suffix_token=secrets.token_urlsafe(10)
    secret:dict=get_user_by_email(extracted_auth_dict['config']['user_email']).get('secrets',{})
    client_secret:str=secret.get(extracted_auth_dict['apikey'],None)

    if not client_secret:
        raise HTTPException(
            status_code=403,
            detail="client secret not found"
        )
    
    auth_code=sha256(client_secret.encode()).hexdigest()[:10]+suffix_token
    ic(auth_code)

    locked_email = session_data.get('locked_email')
    locked_phone = session_data.get('locked_phone')
    lock_method = session_data.get('lock_method')
    prefilled = bool(locked_email or locked_phone)

    jwt_payload = {
        "email": auth_user.get('email') or None,
        "mobile_number": auth_user.get('mobile_number'),
        "name": auth_user.get('name') or auth_user.get('full_name'),
        'profile_picture': auth_user.get('profile_picture'),
        'custom_fields': auth_user.get('custom_fields', {}),
        'auth_provider': auth_user.get('auth_provider', 'unknown'),
        'prefilled': prefilled,
        'lock_method': lock_method or None
    }

    if request:
        jwt_payload['ip'] = request.client.host if request.client else "unknown"
        jwt_payload['browser'] = request.headers.get("User-Agent", "unknown")

    if auth_user.get('auth_provider') == 'password' and 'password' in auth_user:
        jwt_payload['password'] = auth_user['password']

    app_token = generate_jwt_token(jwt_payload, exp_min=60)

    authenticated_values={
        'token':app_token,
        'suffix_token':suffix_token,
        'user_email':extracted_auth_dict['config']['user_email'],
        'apikey':extracted_auth_dict['apikey']
    }
    await redis_set(key=auth_code,value=authenticated_values,exp=300)
    
    redirect_urls = extracted_auth_dict.get('config', {}).get('redirect_urls', {})
    flow_type = extracted_auth_dict.get('flow_type', 'signin')
    
    if flow_type == 'signup':
        base_url = redirect_urls.get('signup_success') or extracted_auth_dict.get('config', {}).get('redirect_url', '/')
    else:
        base_url = redirect_urls.get('signin_success') or extracted_auth_dict.get('config', {}).get('redirect_url', '/')
        
    redirect_url_final = f"{base_url}?token_id={auth_code}"
    if return_json:
        response = JSONResponse(content={"redirect_url": redirect_url_final})
    else:
        response = RedirectResponse(url=redirect_url_final, status_code=302)
    
    # SSO Logic
    sso_config = extracted_auth_dict['config'].get('sso', {})
    if sso_config.get('enabled', False) and request:
        product_id = extracted_auth_dict['apikey']
        user_email = auth_user['email']
        
        # Check if EndUser exists, if not create
        sso_user = get_sso_user(product_id, user_email)
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
            create_sso_user(product_id, sso_user)
            
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
                update_end_user(product_id, sso_user)
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