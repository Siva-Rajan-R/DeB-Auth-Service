from pydantic import BaseModel,Field
from typing import List,Dict,Optional




# Ui Styling Sub Schemas (HELPERS)
class UiStylingBgColorSchema(BaseModel):
    color:Optional[str]=None
    gradient_start:Optional[str]=None
    gradient_end:Optional[str]=None
    gradient_direction:Optional[str]=None



# Ui Styling Schemas (HELPERS)
class UiStylingColorSchema(BaseModel):
    text_color:str

class UiStylingTypographySchema(BaseModel):
    font_family:str
    font_size:str

class UiStylingCardSchema(BaseModel):
    card_bg_color:str
    border_radius:str
    shadow:str
    backdrop_blur:str
    border_width:str
    border_color:str

class UiStylingButtonSchema(BaseModel):
    primary_btn_color:str
    btn_style:str
    input_style:str
    input_border_color:str

class UiStylingLayoutSchema(BaseModel):
    logo_position:str
    social_btn_position:str

class UiStylingBgSchema(BaseModel):
    color:UiStylingBgColorSchema
    pattern:str


class UiStyling(BaseModel):
    colors:UiStylingColorSchema
    typography:UiStylingTypographySchema
    card:UiStylingCardSchema
    buttons:UiStylingButtonSchema
    layout:UiStylingLayoutSchema
    background:UiStylingBgSchema


class UiBrandingSchema(BaseModel):
    name:str
    logo_url:str



# Writable Schemas (MAIN)
class CreateUiSchema(BaseModel):
    user_id:str
    branding:UiBrandingSchema
    styling:UiStyling
    auth_methods:List[str]


class UpdateUiSchema(BaseModel):
    id:str
    user_id:str
    branding:Optional[UiBrandingSchema]=None
    styling:Optional[UiStyling]=None
    auth_methods:List[str]


class DeleteUiSchema(BaseModel):
    id:str
    user_id:str


# Redable Schemas (MAIN)

class GetUiSchema(BaseModel):
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)


class GetByUserUiSchema(BaseModel):
    limit:int=Field(default=10,lt=100)
    offset:int=Field(default=1)


class GetByIdUiSchema(BaseModel):
    id:str
    user_id:str