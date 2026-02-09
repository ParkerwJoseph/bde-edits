from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database.models.document import DocumentStatus, DocumentType, BDEPillar, ChunkType


class DocumentResponse(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    uploaded_by: str
    filename: str
    original_filename: str
    file_type: DocumentType
    file_size: int
    status: DocumentStatus
    total_pages: Optional[int]
    processed_pages: Optional[int]
    error_message: Optional[str]

    # Document overview from Pass 1 analysis
    document_type: Optional[str] = None
    document_title: Optional[str] = None
    document_summary: Optional[str] = None
    key_themes: Optional[str] = None  # JSON array as string

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class ChunkMetadata(BaseModel):
    section_title: Optional[str] = None
    has_numbers: Optional[bool] = None
    has_dates: Optional[bool] = None
    key_entities: Optional[List[str]] = None
    data_type: Optional[str] = None


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    content: str
    summary: str
    previous_context: Optional[str]
    pillar: BDEPillar
    chunk_type: ChunkType
    page_number: int
    chunk_index: int
    confidence_score: Optional[float]
    metadata: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentWithChunksResponse(BaseModel):
    document: DocumentResponse
    chunks: List[ChunkResponse]
    chunk_count: int


class ProcessingStatusResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    total_pages: Optional[int]
    processed_pages: Optional[int]
    error_message: Optional[str]
    chunk_count: int


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus
    message: str
