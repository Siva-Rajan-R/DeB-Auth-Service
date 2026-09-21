from fastapi.exceptions import HTTPException
from configs.mongo_config import db
from input_formats.dict_inputs import User, Configuration
from icecream import ic
from dotenv import load_dotenv
import os

load_dotenv()

USER_COLLECTION_NAME = "dauth_users"
APIKEYS_COLLECTION_NAME = "dauth_apikeys"

def email_key_generator(email: str):
    return email.replace('.', '_').replace('@', '_at_')

async def create_user(user: User):
    try:
        email_key = email_key_generator(user['email'])
        is_user = await get_user_by_email(user['email'])
        if not is_user:
            user_doc = dict(user)
            user_doc['_id'] = email_key
            await db[USER_COLLECTION_NAME].insert_one(user_doc)
        return "User Created Successfully"
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while creating user {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while creating user {e}")

async def get_user_by_email(user_email: str):
    try:
        email_key = email_key_generator(user_email)
        user = await db[USER_COLLECTION_NAME].find_one({"_id": email_key})
        return user
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while get user by id {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while get user by id {e}")

async def create_secrets(email: str, apikey: str, client_secret: str, configurations: Configuration):
    try:
        email_key = email_key_generator(email)
        user = await db[USER_COLLECTION_NAME].find_one({"_id": email_key})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        secrets = user.get('secrets', {})
        cur_no_of_secrets = len(secrets)
        max_keys = user.get('max_keys', 2)

        if cur_no_of_secrets >= max_keys:
            raise HTTPException(status_code=403, detail="max keys limit reached")
        
        secrets[apikey] = client_secret

        if not user.get('remove_branding', False):
            configurations['branding'] = 'DAuth'

        configurations['user_email'] = email
        config_doc = dict(configurations)
        config_doc['_id'] = apikey

        await db[APIKEYS_COLLECTION_NAME].insert_one(config_doc)
        await db[USER_COLLECTION_NAME].update_one({"_id": email_key}, {"$set": {"secrets": secrets}})

        return {'apikey': apikey, 'client_secret': client_secret}
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while adding apikey {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while adding apikey {e}")

async def revoke_secrets(email: str, old_apikey: str, new_apikey: str, new_client_secret: str):
    try:
        email_key = email_key_generator(email)
        user = await db[USER_COLLECTION_NAME].find_one({"_id": email_key})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        secrets = user.get('secrets', {})
        if old_apikey not in secrets:
            raise HTTPException(status_code=404, detail="Apikey not found")
        
        del secrets[old_apikey]

        old_config = await db[APIKEYS_COLLECTION_NAME].find_one({"_id": old_apikey})
        if old_config:
            old_config['_id'] = new_apikey
            await db[APIKEYS_COLLECTION_NAME].insert_one(old_config)
            await db[APIKEYS_COLLECTION_NAME].delete_one({"_id": old_apikey})

        secrets[new_apikey] = new_client_secret
        await db[USER_COLLECTION_NAME].update_one({"_id": email_key}, {"$set": {"secrets": secrets}})

        return "Api key revoked successfully"
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while revoking apikey {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while revoking apikey {e}")

async def regenerate_client_secret(email: str, apikey: str, new_client_secret: str):
    try:
        email_key = email_key_generator(email)
        user = await db[USER_COLLECTION_NAME].find_one({"_id": email_key})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        secrets = user.get('secrets', {})
        if apikey not in secrets:
            raise HTTPException(status_code=404, detail="Apikey not found")
        
        secrets[apikey] = new_client_secret
        await db[USER_COLLECTION_NAME].update_one({"_id": email_key}, {"$set": {"secrets": secrets}})
        
        return "Client secret regenerated successfully"
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while regenerating client secret {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while regenerating client secret {e}")

async def remove_apikey(email: str, apikey: str):
    try:
        email_key = email_key_generator(email)
        user = await db[USER_COLLECTION_NAME].find_one({"_id": email_key})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        secrets = user.get('secrets', {})
        if apikey not in secrets:
            raise HTTPException(status_code=404, detail="Apikey not found")
        
        del secrets[apikey]

        await db[USER_COLLECTION_NAME].update_one({"_id": email_key}, {"$set": {"secrets": secrets}})
        await db[APIKEYS_COLLECTION_NAME].delete_one({"_id": apikey})
        return "Api key removed successfully"
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while removing apikey {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while removing apikey {e}")

async def update_cofigurations(email: str, apikey: str, new_configurations: Configuration):
    try:
        email_key = email_key_generator(email)
        user = await db[USER_COLLECTION_NAME].find_one({"_id": email_key})
        if not user:
            raise HTTPException(status_code=404, detail="User does not exists")
        
        secrets = user.get('secrets', {})
        if apikey not in secrets:
            raise HTTPException(status_code=404, detail="Api key not found")
        
        if not user.get('remove_branding', False):
            new_configurations['branding'] = 'De-Buggers'

        new_configurations['user_email'] = email
        
        await db[APIKEYS_COLLECTION_NAME].update_one({"_id": apikey}, {"$set": dict(new_configurations)})

        return "updated configurations successfully"
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while updating configurations {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while updating configurations {e}")

async def delete_user(user_email: str):
    try:
        email_key = email_key_generator(user_email)
        user_data = await db[USER_COLLECTION_NAME].find_one({"_id": email_key})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        secrets = user_data.get("secrets", {})
        for apikey in secrets.keys():
            await db[APIKEYS_COLLECTION_NAME].delete_one({"_id": apikey})
            
        await db[USER_COLLECTION_NAME].delete_one({"_id": email_key})

        return "User deleted successfully"
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while deleting user {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while deleting user {e}")

async def get_user_secrets(user_email: str):
    try:
        email_key = email_key_generator(user_email)
        user = await db[USER_COLLECTION_NAME].find_one({"_id": email_key})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        final_secrets = []
        secrets = user.get('secrets', {})
        for apikey, client_secret in secrets.items():
            config = await db[APIKEYS_COLLECTION_NAME].find_one({"_id": apikey})
            if config:
                config.pop('_id', None)
                config.pop('user_email', None)
                final_secrets.append({
                    'apikey': apikey,
                    'client_secret': client_secret,
                    'configurations': config
                })
        branding = user.get('remove_branding', False)

        return {'secrets': final_secrets, 'branding': branding}
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while getting user secrets {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while getting user secrets {e}")

async def get_all_users():
    try:
        cursor = db[USER_COLLECTION_NAME].find()
        users = await cursor.to_list(length=None)
        return {u['_id']: u for u in users}
    except Exception as e:
        ic(f"something went wrong while getting all users")
        raise HTTPException(status_code=500, detail=f"something went wrong while getting all users")

async def check_apikey_exists(apikey: str):
    try:
        is_present = await db[APIKEYS_COLLECTION_NAME].find_one({"_id": apikey})
        if not is_present:
            raise HTTPException(status_code=404, detail="Api key doesn't exists")
        is_present.pop('_id', None)
        return is_present
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong while checking apikey {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong while checking apikey {e}")

async def create_debuggers_cred(base_url: str):
    try:
        user = User(
            name="DeB-Auth-System",
            email=os.getenv('DEB_EMAIL'),
            secrets={},
            remove_branding=False,
            max_keys=2
        )

        await create_user(user=user)

        await create_secrets(
            email=os.getenv('DEB_EMAIL', ""),
            apikey=os.getenv("DEB_APIKEY", ""),
            client_secret=os.getenv('DEB_CLIENT_SECRET', ""),
            configurations=Configuration(
                auth_methods=[
                    {"id": "otp", "name": "OTP", "enabled": True},
                    {"id": "google", "name": "Google", "enabled": True},
                    {"id": "github", "name": "GitHub", "enabled": True},
                    {"id": "facebook", "name": "Facebook", "enabled": True}
                ],
                branding="De-Buggers",
                redirect_urls={"signin_success": f"{base_url}/user/create"}
            )
        )

        return "Debuggers Credentials Created Successfully"
    except HTTPException:
        raise
    except Exception as e:
        ic(f"something went wrong creating debuggers cred : {e}")
        raise HTTPException(status_code=500, detail=f"something went wrong creating debuggers cred : {e}")

async def update_user_profile(user_email: str, profile_data: dict):
    try:
        email_key = email_key_generator(user_email)
        await db[USER_COLLECTION_NAME].update_one(
            {"_id": email_key},
            {"$set": profile_data}
        )
        return "Profile updated successfully"
    except Exception as e:
        ic(f"Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")
