import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text
from typing import Optional
from enum import Enum
from pgvector.sqlalchemy import Vector


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    PDF = "pdf"
    PPTX = "pptx"
    DOCX = "docx"
    XLSX = "xlsx"
    AUDIO = "audio"


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    uploaded_by: str = Field(foreign_key="users.id", index=True)

    filename: str = Field(max_length=500)
    original_filename: str = Field(max_length=500)
    file_type: DocumentType
    file_size: int
    file_path: str = Field(max_length=1000)

    # Azure Blob Storage fields
    blob_name: Optional[str] = Field(default=None, max_length=1000, index=True)
    blob_url: Optional[str] = Field(default=None, sa_column=Column(Text))
    signed_url: Optional[str] = Field(default=None, sa_column=Column(Text))
    signed_url_expiry: Optional[datetime] = Field(default=None)
    content_type: Optional[str] = Field(default=None, max_length=255)

    status: DocumentStatus = Field(default=DocumentStatus.PENDING)
    total_pages: Optional[int] = Field(default=None)
    processed_pages: Optional[int] = Field(default=0)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Document overview
    document_type: Optional[str] = Field(default=None, max_length=100)
    document_title: Optional[str] = Field(default=None, max_length=500)
    document_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    key_themes: Optional[str] = Field(default=None, sa_column=Column(Text))
    overview_json: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_stored_in_blob(self) -> bool:
        return self.blob_name is not None

    def is_signed_url_valid(self) -> bool:
        if not self.signed_url or not self.signed_url_expiry:
            return False
        return datetime.utcnow() < self.signed_url_expiry


class BDEPillar(str, Enum):
    FINANCIAL_HEALTH = "financial_health"
    GTM_ENGINE = "gtm_engine"
    CUSTOMER_HEALTH = "customer_health"
    PRODUCT_TECHNICAL = "product_technical"
    OPERATIONAL_MATURITY = "operational_maturity"
    LEADERSHIP_TRANSITION = "leadership_transition"
    ECOSYSTEM_DEPENDENCY = "ecosystem_dependency"
    SERVICE_SOFTWARE_RATIO = "service_software_ratio"
    GENERAL = "general"


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    IMAGE = "image"
    MIXED = "mixed"


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    company_id: str = Field(foreign_key="companies.id", index=True)

    content: str = Field(sa_column=Column(Text))
    summary: str = Field(sa_column=Column(Text))
    previous_context: Optional[str] = Field(default=None, sa_column=Column(Text))

    pillar: BDEPillar = Field(default=BDEPillar.GENERAL, index=True)
    chunk_type: ChunkType = Field(default=ChunkType.TEXT)

    page_number: int
    chunk_index: int
    confidence_score: Optional[float] = Field(default=None)

    metadata_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    embedding: Optional[list] = Field(default=None, sa_column=Column(Vector(3072)))

    created_at: datetime = Field(default_factory=datetime.utcnow)


# Pillar descriptions for LLM context - Concise version optimized for chunking
PILLAR_DESCRIPTIONS = {
    BDEPillar.FINANCIAL_HEALTH: (
        "Quality, predictability, and efficiency of cash flow, earnings, and profitability. "
        "Use for specific dollar amounts, percentages, financial ratios, gross margin, EBITDA, cash position, burn rate, historical financials, and forward projections. "
        "Do not use for revenue generation methods (GTM_ENGINE) or customer retention metrics (CUSTOMER_HEALTH)."
    ),

    BDEPillar.GTM_ENGINE: (
        "Ability to consistently generate, convert, and forecast revenue through effective sales and marketing operations. "
        "Use for pipeline size, coverage, conversion rates, sales cycle length, CAC, lead generation, and forecast accuracy. "
        "Do not use for final revenue amounts (FINANCIAL_HEALTH) or post-sale retention and expansion metrics (CUSTOMER_HEALTH)."
    ),

    BDEPillar.CUSTOMER_HEALTH: (
        "Customer retention, satisfaction, product adoption, and post-sale growth. "
        "Use for GRR, NRR, churn, renewal rate, expansion revenue, NPS, CSAT, cohort retention, and usage/adoption metrics. "
        "Do not use for customer acquisition (GTM_ENGINE) or revenue amounts (FINANCIAL_HEALTH)."
    ),

    BDEPillar.PRODUCT_TECHNICAL: (
        "Scalability, stability, reliability, security, and platform readiness. "
        "Use for uptime, SLA, response time, error rate, MTTR, deployment frequency, test coverage, security certifications, architecture, and API/integration readiness. "
        "Do not use for internal processes (OPERATIONAL_MATURITY) or team structure (LEADERSHIP_TRANSITION)."
    ),

    BDEPillar.OPERATIONAL_MATURITY: (
        "Reliability and scalability of internal processes and execution. "
        "Use for SOPs, onboarding time, project delivery, utilization, support backlog, and manual process count. "
        "Do not use for leadership (LEADERSHIP_TRANSITION) or software quality (PRODUCT_TECHNICAL)."
    ),

    BDEPillar.LEADERSHIP_TRANSITION: (
        "Dependency on founders/executives, succession readiness, and leadership resilience. "
        "Use when named leaders, key-person dependency, decision-making continuity, or governance materially affect outcomes. "
        "Do not use for general team structure without leadership risk (OPERATIONAL_MATURITY)."
    ),

    BDEPillar.ECOSYSTEM_DEPENDENCY: (
        "Risk from reliance on external platforms, ERP ecosystems, or strategic partners. "
        "Use when dependency on external systems, APIs, vendor relationships, or partner tiers materially affects operations, revenue, or strategic positioning. "
        "Do not use for internal integrations (PRODUCT_TECHNICAL) or vendor spend (FINANCIAL_HEALTH)."
    ),

    BDEPillar.SERVICE_SOFTWARE_RATIO: (
        "Revenue scalability and margin efficiency — balance of software versus human-driven services. "
        "Use when revenue growth is constrained by manual services, custom implementations, or support-heavy execution, "
        "or when assessing the potential to productize services into scalable software. "
        "Do not use for total revenue numbers (FINANCIAL_HEALTH) or product architecture/features (PRODUCT_TECHNICAL)."
    ),

    BDEPillar.GENERAL: (
        "Contextual or administrative information (company history, locations, legal structure, TOC, disclaimers). "
        "Use only when no other pillar fits with >50% confidence. "
        "Avoid defaulting here — most business content belongs to a specific pillar."
    ),
}
