from fb_database.main import db
from input_formats.dict_inputs import User
from icecream import ic

USER_CHILD_NAME="DeB-Users"
APIKEYS_CHILD_NAME="DeB-APIKeys"
SECRET_CHILD_NAME="DeB-Secrets"

def create_user(user:User,user_pk:str,user_apikey:str,user_client_secret:str):
    try:
        db.child(USER_CHILD_NAME).child(user_pk).set(user)
        db.child(APIKEYS_CHILD_NAME).child(user_apikey).set(user_pk)
        db.child(SECRET_CHILD_NAME).child(user_client_secret).set(user_pk)


        return "User Created Successfully"
    
    except Exception as e:
        ic(f"something went wrong while creating user {e}")
    
def delete_user(user_pk:str):
    try:
        user_data = db.child(USER_CHILD_NAME).child(user_pk).get().val()
        if not user_data:
            return "User not found"

        apikey = user_data.get("apikey")
        secret=user_data.get("client_secret")
        updates = {
            f"{USER_CHILD_NAME}/{user_pk}": None,
            f"{APIKEYS_CHILD_NAME}/{apikey}": None,
            f"{SECRET_CHILD_NAME}/{secret}": None
        }

        db.update(updates)  # atomic del


        return "User deleted successfully"
    
    except Exception as e:
        ic(f"something went wrong while deleting user {e}")

def get_user_by_id(user_pk:str):
    try:
        user=db.child(USER_CHILD_NAME).child(user_pk).get().val()
        ic(user,user_pk)
        ic(user['client_secret'])
        return user
    except Exception as e:
        ic(f"something went wrong while get user by id {e}")

def get_all_users():
    try:
        return db.child(USER_CHILD_NAME).get().val()
    except Exception as e:
        ic(f"something went wrong while getting all users")

def check_apikey_exists(apikey:str):
    try:
        is_present=db.child(APIKEYS_CHILD_NAME).child(apikey).get().val()

        if not is_present:
            return False
        ic(is_present)
        return is_present
    except Exception as e:
        ic(f"something went wrong while checking apikey {e}")

def check_client_secret_exists(client_secret:str):
    try:
        is_present=db.child(SECRET_CHILD_NAME).child(client_secret).get().val()

        if not is_present:
            return False
        ic(is_present)
        return is_present
    except Exception as e:
        ic(f"something went wrong while checking client secret {e}")
