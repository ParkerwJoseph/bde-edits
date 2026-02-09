import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text
from typing import Optional
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatSession(SQLModel, table=True):
    """A chat session belonging to a user within a tenant."""
    __tablename__ = "chat_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    company_id: Optional[str] = Field(default=None, foreign_key="companies.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)

    # Session metadata
    title: str = Field(max_length=255, default="New Chat")

    # Optional: filter to specific documents for this session
    document_ids_json: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessageModel(SQLModel, table=True):
    """A single message in a chat session."""
    __tablename__ = "chat_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="chat_sessions.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)

    # Message content
    role: MessageRole
    content: str = Field(sa_column=Column(Text))

    # For assistant messages, store the sources
    sources_json: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Token usage for assistant messages
    usage_stats_json: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
