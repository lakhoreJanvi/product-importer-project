from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class ProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    price: Optional[str] = None
    active: Optional[bool] = True

class ProductRead(ProductCreate):
    id: int

    class Config:
        orm_mode = True

class WebhookBase(BaseModel):
    url: HttpUrl
    event_type: str
    enabled: bool = True

class WebhookCreate(WebhookBase):
    pass

class WebhookUpdate(WebhookBase):
    pass

class WebhookRead(WebhookBase):
    id: int

    class Config:
        orm_mode = True 

class WebhookOut(WebhookBase):
    id: int
    class Config:
        orm_mode = True