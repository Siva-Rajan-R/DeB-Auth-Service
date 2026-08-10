from fastapi.exceptions import HTTPException
from configs.mongo_config import db
from schemas.db_schemas.end_user_schema import Role
from icecream import ic

ROLES_COLLECTION = "dauth_roles"

async def create_role(product_id: str, role: Role):
    try:
        role_dict = role.dict()
        role_dict['_id'] = f"{product_id}_{role.role_id}"
        role_dict['product_id'] = product_id
        await db[ROLES_COLLECTION].insert_one(role_dict)
        return role
    except Exception as e:
        ic(f"Error creating role: {e}")
        raise HTTPException(status_code=500, detail="Failed to create role")

async def get_role(product_id: str, role_id: str):
    try:
        role_data = await db[ROLES_COLLECTION].find_one({"_id": f"{product_id}_{role_id}"})
        if role_data:
            role_data.pop('_id', None)
            role_data.pop('product_id', None)
            return Role(**role_data)
        return None
    except Exception as e:
        ic(f"Error getting role: {e}")
        raise HTTPException(status_code=500, detail="Failed to get role")

async def get_all_roles(product_id: str):
    try:
        cursor = db[ROLES_COLLECTION].find({"product_id": product_id})
        roles = await cursor.to_list(length=None)
        result = []
        for r in roles:
            r.pop('_id', None)
            r.pop('product_id', None)
            result.append(Role(**r))
        return result
    except Exception as e:
        ic(f"Error getting all roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to get roles")

async def delete_role(product_id: str, role_id: str):
    try:
        await db[ROLES_COLLECTION].delete_one({"_id": f"{product_id}_{role_id}"})
        return True
    except Exception as e:
        ic(f"Error deleting role: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete role")
