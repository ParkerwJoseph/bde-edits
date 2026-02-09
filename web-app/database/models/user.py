import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
from typing import Optional


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    azure_oid: str = Field(index=True, max_length=255)  # Azure AD Object ID
    azure_tid: str = Field(index=True, max_length=255)  # Azure AD Tenant ID
    tenant_id: Optional[str] = Field(default=None, foreign_key="tenants.id", index=True)  # BDE Tenant
    role_id: Optional[str] = Field(default=None, foreign_key="roles.id", index=True)
    email: Optional[str] = Field(default=None, index=True, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    first_login_at: Optional[datetime] = Field(default=None)
    last_login_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
