import uuid
from sqlmodel import SQLModel, Field
from typing import Optional


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)  # e.g., "users:read", "tenants:create"
    category: str = Field(index=True, max_length=50)  # e.g., "users", "tenants", "reports"
    description: Optional[str] = Field(default=None, max_length=500)


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"

    role_id: str = Field(foreign_key="roles.id", primary_key=True)
    permission_id: str = Field(foreign_key="permissions.id", primary_key=True)
