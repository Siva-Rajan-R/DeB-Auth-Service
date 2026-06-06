from pydantic import BaseModel
from typing import Optional,List
from core.data_formats.enums.field_enum import FieldTypeEnums


class BaseFieldsSchema(BaseModel):
    label_name:str
    field_name:str
    type:FieldTypeEnums
    required:bool
    row_number:int


class SignUpFieldSchema(BaseModel):
    fields:List[BaseFieldsSchema]