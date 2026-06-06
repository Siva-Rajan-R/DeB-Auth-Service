import uuid

def generate_unique_id(data:str)->str:
    try:
        return uuid.uuid5(uuid.uuid4(),name=data).__str__()
    
    except Exception as e:
        raise RuntimeError(
            f"something went erong while generating uuid {e}"
        )
    
# print(type(generate_unique_id("hello")))