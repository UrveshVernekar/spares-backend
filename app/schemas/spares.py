from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class SpareItem(BaseModel):
    id: Optional[int] = None

    material: Optional[str] = None
    description: Optional[str] = None
    branch: Optional[str] = None
    plant: Optional[int] = None

    abc: Optional[str] = None

    stock: Optional[int] = None
    netavl: Optional[int] = None

    weekly: Optional[float] = None
    avg6m: Optional[float] = None
    lysm: Optional[int] = None

    sugqty: Optional[int] = None

    value: Optional[str] = None
    status: Optional[str] = None

    trend: Optional[bool] = None

    class Config:
        from_attributes = True

class SparesResponse(BaseModel):
    success: bool
    count: int
    data: List[SpareItem]
