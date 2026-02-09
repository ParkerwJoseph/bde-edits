from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    query: str
    session_id: Optional[str] = None  # If provided, continue existing session
    company_id: Optional[str] = None  # If provided, search only this company's documents
    document_ids: Optional[List[str]] = None  # If None, search all company documents
    conversation_history: Optional[List[ChatMessage]] = None  # Deprecated: use session_id instead
    top_k: Optional[int] = 5


class SourceInfo(BaseModel):
    """Information about a source chunk."""
    chunk_id: str
    document_id: str
    document_name: str  # Original filename of the document
    page_number: int
    pillar: str
    pillar_label: str  # Human-readable pillar name
    similarity: float
    summary: str
    # Connector-specific fields
    source_type: str = "document"  # "document" or "connector"
    connector_type: Optional[str] = None  # e.g., "quickbooks"
    entity_type: Optional[str] = None  # e.g., "invoice", "customer"
    entity_name: Optional[str] = None  # Human-readable entity name


class ChunkInfo(BaseModel):
    """Full chunk information returned in response."""
    id: str
    document_id: str
    content: str
    summary: Optional[str]
    previous_context: Optional[str]
    pillar: str
    chunk_type: str
    page_number: int
    similarity: float


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    answer: str
    sources: List[SourceInfo]
    chunks: List[ChunkInfo]
    usage_stats: Dict[str, Any]
    session_id: Optional[str] = None  # The session ID for this conversation


class SearchRequest(BaseModel):
    """Request body for semantic search endpoint."""
    query: str
    document_ids: Optional[List[str]] = None
    top_k: Optional[int] = 10
    similarity_threshold: Optional[float] = 0.5


class SearchResponse(BaseModel):
    """Response from search endpoint."""
    chunks: List[ChunkInfo]
    total: int


# Chat Session Schemas

class ChatSessionCreate(BaseModel):
    """Request to create a new chat session."""
    title: Optional[str] = "New Chat"
    company_id: Optional[str] = None
    document_ids: Optional[List[str]] = None


class ChatSessionUpdate(BaseModel):
    """Request to update a chat session."""
    title: Optional[str] = None
    document_ids: Optional[List[str]] = None


class ChatMessageResponse(BaseModel):
    """A message in a chat session response."""
    id: str
    role: str
    content: str
    sources: Optional[List[SourceInfo]] = None
    usage_stats: Optional[Dict[str, Any]] = None
    created_at: datetime


class ChatSessionResponse(BaseModel):
    """Response for a chat session."""
    id: str
    title: str
    company_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime


class ChatSessionDetailResponse(BaseModel):
    """Response for a chat session with messages."""
    id: str
    title: str
    company_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    messages: List[ChatMessageResponse]
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    """Response for listing chat sessions."""
    sessions: List[ChatSessionResponse]
    total: int
