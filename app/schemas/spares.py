from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class SpareItem(BaseModel):
    id: Optional[int] = None
    plant: Optional[str] = None
    billt: Optional[str] = None
    dv: Optional[str] = None
    dchl: Optional[str] = None
    po_number: Optional[str] = None
    po_date: Optional[date] = None
    city: Optional[str] = None
    bill_date: Optional[date] = None
    bill_doc: Optional[str] = None
    sold_to_pt: Optional[str] = None
    ship_to_party_name: Optional[str] = None
    ship_to: Optional[str] = None
    sold_party_name: Optional[str] = None
    material_code: Optional[str] = None
    material_desc: Optional[str] = None
    material_group: Optional[str] = None
    inventory_qty: Optional[float] = None
    dealer_price: Optional[float] = None
    basic_rate: Optional[float] = None
    net_value: Optional[float] = None
    tax: Optional[float] = None
    gross_value: Optional[float] = None
    delivery: Optional[str] = None

    class Config:
        from_attributes = True

class SparesResponse(BaseModel):
    success: bool
    count: int
    data: List[SpareItem]
