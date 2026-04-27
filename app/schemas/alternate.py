# app/schemas/alternate.py
from pydantic import BaseModel
from datetime import date
from typing import Optional


class AlternatePartBase(BaseModel):
    Master_Mat: Optional[str] = None
    Master_Material_Description: Optional[str] = None
    Substitute: Optional[str] = None
    Substitute_Material_Description: Optional[str] = None
    Material_T: Optional[str] = None
    Branch: Optional[str] = None
    Stock_Lo: Optional[int] = None
    Obsolete: Optional[str] = None
    Bidi_Flag: Optional[str] = None
    Doc_Type: Optional[str] = None
    Purch_Org: Optional[str] = None
    CoCode: Optional[str] = None
    Plant: Optional[str] = None
    Valid_From: Optional[date] = None
    Valid_To: Optional[date] = None


class AlternateUploadResponse(BaseModel):
    message: str
    total_records: int
    inserted: int
    updated: int