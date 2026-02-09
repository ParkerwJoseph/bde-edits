import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field


class Company(SQLModel, table=True):
    """A company within a tenant. Documents are organized by company."""
    __tablename__ = "companies"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    name: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
