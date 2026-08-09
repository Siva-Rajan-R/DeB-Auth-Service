from fastapi.exceptions import HTTPException
from configs.firebase_config import db
from schemas.db_schemas.end_user_schema import EndUser
from icecream import ic

END_USERS_CHILD = "DeB-EndUsers"

def identifier_key_generator(identifier: str):
    return identifier.replace('.', '_').replace('@', '_at_').replace('+', '_plus_')

def create_end_user(product_id: str, user: EndUser):
    try:
        user_id = user.email or user.mobile_number or user.id
        key = identifier_key_generator(user_id)
        user_dict = user.dict()
        db.child(END_USERS_CHILD).child(product_id).child(key).set(user_dict)
        return user
    except Exception as e:
        ic(f"Error creating end user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create end user")

def get_end_user_by_identifier(product_id: str, identifier: str):
    try:
        key = identifier_key_generator(identifier)
        user_data = db.child(END_USERS_CHILD).child(product_id).child(key).get().val()
        if user_data:
            return EndUser(**user_data)
        return None
    except Exception as e:
        ic(f"Error getting end user: {e}")
        raise HTTPException(status_code=500, detail="Failed to get end user")

def get_end_user_by_email(product_id: str, email: str):
    return get_end_user_by_identifier(product_id, email)

def update_end_user(product_id: str, user: EndUser):
    try:
        user_id = user.email or user.mobile_number or user.id
        key = identifier_key_generator(user_id)
        db.child(END_USERS_CHILD).child(product_id).child(key).update(user.dict())
        return user
    except Exception as e:
        ic(f"Error updating end user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update end user")
        
def get_all_end_users(product_id: str):
    try:
        users = db.child(END_USERS_CHILD).child(product_id).get().val()
        if users:
            return [EndUser(**u) for u in users.values() if u]
        return []
    except Exception as e:
        ic(f"Error getting all end users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get end users")
