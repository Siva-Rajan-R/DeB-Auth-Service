from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from operations.fb_operations.end_users_crud import get_all_end_users, create_end_user, update_end_user
from operations.fb_operations.roles_crud import get_all_roles, create_role, delete_role
from operations.redis_operations.session_manager import revoke_global_session, revoke_product_session
from schemas.db_schemas.end_user_schema import EndUser, Role
from api.dependencies.token_verification import verify_user
from icecream import ic

router = APIRouter(
    tags=["Admin Routes"],
    prefix="/admin"
)

def get_product_id(request: Request):
    apikey = request.headers.get("x-api-key")
    if not apikey:
        raise HTTPException(status_code=400, detail="Missing x-api-key header")
    return apikey

@router.get("/users", response_model=List[EndUser])
def get_users(product_id: str = Depends(get_product_id), developer_email: str = Depends(verify_user)):
    return get_all_end_users(product_id)

@router.post("/users", response_model=EndUser)
def add_user(user: EndUser, product_id: str = Depends(get_product_id), developer_email: str = Depends(verify_user)):
    return create_end_user(product_id, user)

@router.put("/users", response_model=EndUser)
def edit_user(user: EndUser, product_id: str = Depends(get_product_id), developer_email: str = Depends(verify_user)):
    return update_end_user(product_id, user)

@router.get("/roles", response_model=List[Role])
def get_roles(product_id: str = Depends(get_product_id), developer_email: str = Depends(verify_user)):
    return get_all_roles(product_id)

@router.post("/roles", response_model=Role)
def add_role(role: Role, product_id: str = Depends(get_product_id), developer_email: str = Depends(verify_user)):
    return create_role(product_id, role)

@router.delete("/roles/{role_id}")
def remove_role(role_id: str, product_id: str = Depends(get_product_id), developer_email: str = Depends(verify_user)):
    return delete_role(product_id, role_id)

@router.delete("/sessions/{session_type}/{session_id}")
async def revoke_session(session_type: str, session_id: str, product_id: str = Depends(get_product_id), developer_email: str = Depends(verify_user)):
    if session_type == "global":
        await revoke_global_session(session_id)
    elif session_type == "product":
        await revoke_product_session(session_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid session type")
    return {"status": "success", "message": "Session revoked"}
