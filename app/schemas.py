# app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List

class InvoiceCreateResponse(BaseModel):
    id: int
    state: str

class FieldExtraction(BaseModel):
    provider_name: Optional[str]
    invoice_number: Optional[str]
    issue_date: Optional[str]
    due_date: Optional[str]
    total_amount: Optional[str]
    taxes: Optional[str]
    extras: Optional[Dict[str,Any]] = {}

class InvoiceStatus(BaseModel):
    id: int
    state: str
    extracted: Optional[FieldExtraction] = None
    history: Optional[List[Dict[str,str]]] = []
