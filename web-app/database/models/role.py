import uuid
from sqlmodel import SQLModel, Field
from typing import Optional
from enum import Enum


class RoleLevel(str, Enum):
    PLATFORM = "platform"  # BCP-level roles
    TENANT = "tenant"      # Company-level roles


class RoleName(str, Enum):
    SUPER_ADMIN = "super_admin"      # BCP - full system access
    BCP_ANALYST = "bcp_analyst"      # BCP - read-only cross-tenant analytics
    TENANT_ADMIN = "tenant_admin"    # Company - manage own tenant
    TENANT_USER = "tenant_user"      # Company - basic user


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(unique=True, index=True, max_length=50)  # Store as string, not enum
    level: str = Field(index=True, max_length=20)  # Store as string, not enum
    description: Optional[str] = Field(default=None, max_length=500)
