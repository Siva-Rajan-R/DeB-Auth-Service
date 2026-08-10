from fastapi.exceptions import HTTPException
from configs.mongo_config import db
from schemas.db_schemas.end_user_schema import EndUser
from icecream import ic

END_USERS_COLLECTION = "dauth_end_users"

def identifier_key_generator(identifier: str):
    return identifier.replace('.', '_').replace('@', '_at_').replace('+', '_plus_')

async def create_end_user(product_id: str, user: EndUser):
    try:
        user_id = user.email or user.mobile_number or user.id
        key = identifier_key_generator(user_id)
        user_dict = user.dict()
        user_dict['_id'] = f"{product_id}_{key}"
        user_dict['product_id'] = product_id
        
        await db[END_USERS_COLLECTION].insert_one(user_dict)
        return user
    except Exception as e:
        ic(f"Error creating end user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create end user")

async def get_end_user_by_identifier(product_id: str, identifier: str):
    try:
        key = identifier_key_generator(identifier)
        user_data = await db[END_USERS_COLLECTION].find_one({"_id": f"{product_id}_{key}"})
        if user_data:
            user_data.pop('_id', None)
            user_data.pop('product_id', None)
            return EndUser(**user_data)
        return None
    except Exception as e:
        ic(f"Error getting end user: {e}")
        raise HTTPException(status_code=500, detail="Failed to get end user")

async def get_end_user_by_email(product_id: str, email: str):
    return await get_end_user_by_identifier(product_id, email)

async def update_end_user(product_id: str, user: EndUser):
    try:
        user_id = user.email or user.mobile_number or user.id
        key = identifier_key_generator(user_id)
        user_dict = user.dict()
        
        await db[END_USERS_COLLECTION].update_one(
            {"_id": f"{product_id}_{key}"},
            {"$set": user_dict}
        )
        return user
    except Exception as e:
        ic(f"Error updating end user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update end user")
        
async def get_all_end_users(product_id: str):
    try:
        cursor = db[END_USERS_COLLECTION].find({"product_id": product_id})
        users = await cursor.to_list(length=None)
        result = []
        for u in users:
            u.pop('_id', None)
            u.pop('product_id', None)
            result.append(EndUser(**u))
        return result
    except Exception as e:
        ic(f"Error getting all end users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get end users")
