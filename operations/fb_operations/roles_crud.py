from fastapi.exceptions import HTTPException
from configs.firebase_config import db
from schemas.db_schemas.end_user_schema import Role
from icecream import ic

ROLES_CHILD = "DeB-Roles"

def create_role(product_id: str, role: Role):
    try:
        db.child(ROLES_CHILD).child(product_id).child(role.role_id).set(role.dict())
        return role
    except Exception as e:
        ic(f"Error creating role: {e}")
        raise HTTPException(status_code=500, detail="Failed to create role")

def get_role(product_id: str, role_id: str):
    try:
        role_data = db.child(ROLES_CHILD).child(product_id).child(role_id).get().val()
        if role_data:
            return Role(**role_data)
        return None
    except Exception as e:
        ic(f"Error getting role: {e}")
        raise HTTPException(status_code=500, detail="Failed to get role")

def get_all_roles(product_id: str):
    try:
        roles = db.child(ROLES_CHILD).child(product_id).get().val()
        if roles:
            return [Role(**r) for r in roles.values() if r]
        return []
    except Exception as e:
        ic(f"Error getting all roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to get roles")

def delete_role(product_id: str, role_id: str):
    try:
        db.child(ROLES_CHILD).child(product_id).child(role_id).remove()
        return True
    except Exception as e:
        ic(f"Error deleting role: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete role")
