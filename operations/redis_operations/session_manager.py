import time
import uuid
from operations.redis_operations.handlers import redis_set, redis_get, redis_unlink
from schemas.db_schemas.end_user_schema import GlobalSession, ProductSession

GLOBAL_SESSION_PREFIX = "global_session:"
PRODUCT_SESSION_PREFIX = "product_session:"

async def create_global_session(user_id: str, ip: str, device: str, ttl: int = 86400 * 7):
    session_id = str(uuid.uuid4())
    now = time.time()
    session = GlobalSession(
        session_id=session_id,
        user_id=user_id,
        created_at=now,
        last_activity=now,
        expires_at=now + ttl,
        device_info=device,
        ip_info=ip
    )
    await redis_set(f"{GLOBAL_SESSION_PREFIX}{session_id}", session.dict(), exp=ttl)
    return session

async def get_global_session(session_id: str):
    data = await redis_get(f"{GLOBAL_SESSION_PREFIX}{session_id}")
    if data:
        return GlobalSession(**data)
    return None

async def extend_global_session(session_id: str, ttl: int = 86400 * 7):
    session = await get_global_session(session_id)
    if session:
        now = time.time()
        session.last_activity = now
        session.expires_at = now + ttl
        await redis_set(f"{GLOBAL_SESSION_PREFIX}{session_id}", session.dict(), exp=ttl)
        return session
    return None

async def revoke_global_session(session_id: str):
    await redis_unlink(f"{GLOBAL_SESSION_PREFIX}{session_id}")

async def create_product_session(global_session_id: str, product_id: str, user_id: str, ttl: int = 86400):
    session_id = str(uuid.uuid4())
    now = time.time()
    session = ProductSession(
        session_id=session_id,
        global_session_id=global_session_id,
        product_id=product_id,
        user_id=user_id,
        created_at=now,
        expires_at=now + ttl
    )
    await redis_set(f"{PRODUCT_SESSION_PREFIX}{session_id}", session.dict(), exp=ttl)
    return session

async def get_product_session(session_id: str):
    data = await redis_get(f"{PRODUCT_SESSION_PREFIX}{session_id}")
    if data:
        return ProductSession(**data)
    return None

async def revoke_product_session(session_id: str):
    await redis_unlink(f"{PRODUCT_SESSION_PREFIX}{session_id}")
