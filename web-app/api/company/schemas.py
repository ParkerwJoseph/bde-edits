from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CompanyCreate(BaseModel):
    name: str


class CompanyUpdate(BaseModel):
    name: Optional[str] = None


class CompanyResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    companies: list[CompanyResponse]
    total: int
