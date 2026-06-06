from uuid import UUID,uuid5,uuid4



def generate_uuid()->str:
    return str(uuid5(uuid4(),uuid4().__str__()))