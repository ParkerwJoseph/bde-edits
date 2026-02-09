import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
from typing import Optional
from enum import Enum


class TenantStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    azure_tenant_id: Optional[str] = Field(default=None, unique=True, index=True, max_length=255)
    company_name: str = Field(max_length=255)
    status: TenantStatus = Field(default=TenantStatus.PENDING)
    onboarding_code: Optional[str] = Field(default=None, unique=True, index=True, max_length=64)
    onboarding_code_expiry: Optional[datetime] = Field(default=None)
    consent_timestamp: Optional[datetime] = Field(default=None)
    is_platform_tenant: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
