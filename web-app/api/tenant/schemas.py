from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from database.models.tenant import TenantStatus


class TenantCreate(BaseModel):
    company_name: str


class TenantUpdate(BaseModel):
    company_name: Optional[str] = None
    status: Optional[TenantStatus] = None


class TenantResponse(BaseModel):
    id: str
    azure_tenant_id: Optional[str]
    company_name: str
    status: TenantStatus
    is_platform_tenant: bool
    consent_timestamp: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    tenants: list[TenantResponse]
    total: int


class OnboardingPackage(BaseModel):
    tenant_id: str
    company_name: str
    onboarding_url: str
    onboarding_code: str
    expires_at: datetime


class OnboardingValidation(BaseModel):
    valid: bool
    tenant_id: Optional[str] = None
    company_name: Optional[str] = None
    error: Optional[str] = None
