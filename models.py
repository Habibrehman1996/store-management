from sqlmodel import SQLModel, Field
from datetime import date
from typing import Optional

class Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    quantity: int
    price: float

class ItemCreate(SQLModel):
    name: str
    quantity: int
    price: float

class Sale(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="item.id")
    quantity: int
    total: float
    sale_date: date = Field(default_factory=date.today)

class SaleCreate(SQLModel):
    item_id: int
    quantity: int

class CustomerQuery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_name: str
    query: str
    response: str

class CustomerQueryCreate(SQLModel):
    customer_name: str
    query: str