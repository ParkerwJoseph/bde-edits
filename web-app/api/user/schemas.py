from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from database.models.role import RoleName


class UserResponse(BaseModel):
    id: str
    azure_oid: str
    azure_tid: str
    tenant_id: Optional[str]
    role_id: Optional[str]
    email: Optional[str]
    display_name: Optional[str]
    is_active: bool
    first_login_at: Optional[datetime]
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class UserWithDetails(BaseModel):
    id: str
    email: Optional[str]
    display_name: Optional[str]
    is_active: bool
    first_login_at: Optional[datetime]
    last_login_at: Optional[datetime]
    created_at: datetime
    tenant_name: Optional[str]
    role_name: Optional[str]

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: list[UserWithDetails]
    total: int


class UserRoleUpdate(BaseModel):
    role_name: RoleName


class UserStatusUpdate(BaseModel):
    is_active: bool
