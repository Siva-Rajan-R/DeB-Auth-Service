from fastapi.exceptions import HTTPException
from configs.firebase_config import db
from input_formats.dict_inputs import User
from icecream import ic
from dotenv import load_dotenv
from fastapi import HTTPException,Request
import os
from input_formats.dict_inputs import Configuration,AuthMethods
load_dotenv()

USER_CHILD_NAME="DeB-Users"
APIKEYS_CHILD_NAME="DeB-APIKeys"

def email_key_generator(email:str):
    return email.replace('.','_').replace('@','_at_')

def create_user(user:User):
    try:
        email_key = email_key_generator(user['email'])
        is_user=get_user_by_email(user['email'])
        ic(is_user)
        if not is_user:
            db.child(USER_CHILD_NAME).child(email_key).set(user) #{ secrets : { user_apikey : user_client_secret }, 'email': user.email, 'full_name': user.full_name,remove_branding:true | False,max_keys:2}

        return "User Created Successfully"
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while creating user {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while creating user {e}"
        )

def create_secrets(email:str,apikey:str,client_sceret:str,configurations:Configuration):
    try:
        email_key=email_key_generator(email)
        user=db.child(USER_CHILD_NAME).child(email_key).get().val()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        cur_no_of_secrets=len(user.get('secrets',{}))
        max_keys=user.get('max_keys')

        if cur_no_of_secrets>=max_keys:
            raise HTTPException(
                status_code=403,
                detail="max keys limit reached"
            )
        
        if user.get('secrets',None):
            user['secrets'][apikey]=client_sceret
        else:
            user['secrets']={apikey:client_sceret}

        
        ic(user.get('remove_branding',False))
        if not user.get('remove_branding',False):
            configurations['branding']='De-Buggers'

        configurations['user_email']=email
        ic(configurations)
        db.child(APIKEYS_CHILD_NAME).child(apikey).set(configurations)
        db.child(USER_CHILD_NAME).child(email_key).set(user)

        return "Api key added successfully"
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while adding apikey {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while adding apikey {e}"
        )

def revoke_secrets(email:str,old_apikey:str,new_apikey:str,new_client_secret:str):
    try:
        email_key=email_key_generator(email)

        user=db.child(USER_CHILD_NAME).child(email_key).get().val()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        secrets:dict=user.get('secrets',{})
        if not secrets.get(old_apikey,None):
            raise HTTPException(
                status_code=404,
                detail="Apikey not found"
            )
        
        del secrets[old_apikey]

        old_config_q=db.child(APIKEYS_CHILD_NAME).child(old_apikey)
        old_configurations=old_config_q.get().val()
        updates = {
            f"{APIKEYS_CHILD_NAME}/{old_apikey}": None,
        }
        db.update(updates)  # atomic del

        secrets[new_apikey]=new_client_secret
        user['secrets']=secrets
        db.child(USER_CHILD_NAME).child(email_key).set(user)

        db.child(APIKEYS_CHILD_NAME).child(new_apikey).set(old_configurations)

        return "Api key revoked successfully"
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while revoking apikey {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while revoking apikey {e}"
        )

def remove_apikey(email:str,apikey:str):
    try:
        email_key=email_key_generator(email)
        user=db.child(USER_CHILD_NAME).child(email_key).get().val()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        secrets=user.get('secrets',{})
        if not secrets.get(apikey,None):
            raise HTTPException(
                status_code=404,
                detail="Apikey not found"
            )
        
        del secrets[apikey]

        user['secrets']=secrets
        db.child(USER_CHILD_NAME).child(email_key).set(user)
        db.update({f"{APIKEYS_CHILD_NAME}/{apikey}": None})  # atomic del
        return "Api key removed successfully"
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while removing apikey {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while removing apikey {e}"
        )

def update_cofigurations(email:str,apikey:str,new_configurations:Configuration):
    try:
        email_key=email_key_generator(email)
        user=db.child(USER_CHILD_NAME).child(email_key).get().val()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User does not exists"
            )
        
        secrets=user.get('secrets',{})
        if not secrets.get(apikey,None):
            raise HTTPException(
                status_code=404,
                detail="Api key not found"
            )
        
        ic(user.get('remove_branding',False))
        if not user.get('remove_branding',False):
            new_configurations['branding']='De-Buggers'

        new_configurations['user_email']=email
        
        ic(new_configurations)
        update={
            f'{APIKEYS_CHILD_NAME}/{apikey}':new_configurations
        }

        db.update(update)

        return "updated configurations successfully"
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while updating configurations {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while updating configurations {e}"
        )
    
def delete_user(user_email:str):
    try:
        email_key=email_key_generator(user_email)
        user_data = db.child(USER_CHILD_NAME).child(email_key).get().val()
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        apikey = user_data.get("apikey")
        updates = {
            f"{USER_CHILD_NAME}/{email_key}": None,
            f"{APIKEYS_CHILD_NAME}/{apikey}": None,
        }

        db.update(updates)  # atomic del


        return "User deleted successfully"
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while deleting user {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while deleting user {e}"
        )

def get_user_by_email(user_email:str):
    try:
        email_key=email_key_generator(user_email)
        user=db.child(USER_CHILD_NAME).child(email_key).get().val()
        ic(user,email_key)
        return user
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while get user by id {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while get user by id {e}"
        )

def get_user_secrets(user_email:str):
    try:
        email_key=email_key_generator(user_email)
        user=db.child(USER_CHILD_NAME).child(email_key).get().val()
        ic(user,email_key)
        final_secrets=[]
        secrets:dict=user.get('secrets',{})
        for apikey,client_secret in secrets.items():
            config=db.child(APIKEYS_CHILD_NAME).child(apikey).get().val()
            ic(apikey,client_secret,config)
            del config['user_email']
            final_secrets.append(
                {
                    'apikey':apikey,
                    'client_secret':client_secret,
                    'configurations':config
                }
            )
        branding=user.get('remove_branding',False)

        return {'secrets':final_secrets,'branding':branding}
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while get user by id {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while get user by id {e}"
        )

def get_all_users():
    try:
        return db.child(USER_CHILD_NAME).get().val()
    except Exception as e:
        ic(f"something went wrong while getting all users")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while getting all users"
        )

def check_apikey_exists(apikey:str):
    try:
        is_present=db.child(APIKEYS_CHILD_NAME).child(apikey).get().val()

        if not is_present:
            raise HTTPException(
                status_code=404,
                detail="Api key doesn't exists"
            )
        ic(is_present)
        return is_present
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong while checking apikey {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong while checking apikey {e}"
        )


def create_debuggers_cred(base_url:str):
    try:

        user=User(
                name="DeB-Auth-System",
                email=os.getenv('DEB_EMAIL'),
                secrets={},
                remove_branding=False,
                max_keys=2
            )

        create_user(user=user)

        create_secrets(
            email=os.getenv('DEB_EMAIL'),
            apikey=os.getenv("DEB_APIKEY"),
            client_sceret=os.getenv('DEB_CLIENT_SECRET'),
            configurations=Configuration(
                auth_methods=[AuthMethods.otp,AuthMethods.google,AuthMethods.github],
                branding="De-Buggers",
                redirect_url=f"https://deb-auth-api.onrender.com/user/create"
            )
        )

        return "Debuggers Credentials Created Successfully"
    
    except HTTPException:
        raise

    except Exception as e:
        ic(f"something went wrong creating debuggers cred : {e}")
        raise HTTPException(
            status_code=500,
            detail=f"something went wrong creating debuggers cred : {e}"
        )
