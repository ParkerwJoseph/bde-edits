"""Database models for external data connectors (QuickBooks, Salesforce, etc.)"""
import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text, JSON, ARRAY, String, Enum as SAEnum
from typing import Optional, List
from enum import Enum
from pgvector.sqlalchemy import Vector


class ConnectorType(str, Enum):
    """Supported connector types"""
    QUICKBOOKS = "quickbooks"
    CARBONVOICE = "carbonvoice"
    # Future connectors
    # SALESFORCE = "salesforce"
    # HUBSPOT = "hubspot"
    # XERO = "xero"


class ConnectorStatus(str, Enum):
    """Connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"  # Token expired, needs re-auth
    ERROR = "error"


class SyncStatus(str, Enum):
    """Sync operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ConnectorConfig(SQLModel, table=True):
    """
    Stores connector configuration and OAuth tokens.
    One record per company-connector combination.
    """
    __tablename__ = "connector_configs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    company_id: str = Field(foreign_key="companies.id", index=True)

    # Connector identification
    connector_type: ConnectorType = Field(
        sa_column=Column(String(50), index=True),
    )
    connector_status: ConnectorStatus = Field(
        default=ConnectorStatus.DISCONNECTED,
        sa_column=Column(String(50)),
    )

    # External system identification
    external_company_id: Optional[str] = Field(default=None, max_length=255)  # e.g., QuickBooks realm_id
    external_company_name: Optional[str] = Field(default=None, max_length=500)

    # OAuth tokens (encrypted at rest via application layer)
    access_token: Optional[str] = Field(default=None, sa_column=Column(Text))
    refresh_token: Optional[str] = Field(default=None, sa_column=Column(Text))
    token_expiry: Optional[datetime] = Field(default=None)
    token_type: Optional[str] = Field(default=None, max_length=50)  # e.g., "Bearer"

    # Discovered entities with their availability (populated after OAuth)
    available_entities: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    # e.g., {"invoice": {"count": 234, "available": true}, "customer": {"count": 45, "available": true}}

    # User-selected entities to sync
    enabled_entities: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    # e.g., ["invoice", "customer", "profit_loss", "balance_sheet"]

    # Sync settings
    sync_settings: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    # e.g., {"date_range_months": 12, "sync_frequency": "daily"}

    # Sync tracking
    last_sync_at: Optional[datetime] = Field(default=None)
    last_sync_status: Optional[SyncStatus] = Field(default=None)
    last_sync_error: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Metadata
    connected_by: Optional[str] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_token_valid(self) -> bool:
        """Check if access token is still valid"""
        if not self.access_token or not self.token_expiry:
            return False
        return datetime.utcnow() < self.token_expiry

    def needs_token_refresh(self, buffer_minutes: int = 5) -> bool:
        """Check if token needs refresh (within buffer of expiry)"""
        if not self.token_expiry:
            return True
        from datetime import timedelta
        return datetime.utcnow() + timedelta(minutes=buffer_minutes) >= self.token_expiry


class ConnectorSyncLog(SQLModel, table=True):
    """
    Tracks individual sync operations for audit and debugging.
    """
    __tablename__ = "connector_sync_logs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    connector_config_id: str = Field(foreign_key="connector_configs.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    company_id: str = Field(foreign_key="companies.id", index=True)

    # Sync details
    sync_status: SyncStatus = Field(default=SyncStatus.PENDING)
    sync_type: str = Field(max_length=50)  # "full" or "delta"

    # Progress tracking
    entities_requested: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    entities_completed: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    total_records_fetched: int = Field(default=0)
    total_records_processed: int = Field(default=0)

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    # Error tracking
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    error_details: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Triggered by
    triggered_by: Optional[str] = Field(default=None, foreign_key="users.id")  # NULL if scheduled


class ConnectorRawData(SQLModel, table=True):
    """
    Stores raw data fetched from connectors before processing.
    This is the source of truth for connector data.
    """
    __tablename__ = "connector_raw_data"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    connector_config_id: str = Field(foreign_key="connector_configs.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    company_id: str = Field(foreign_key="companies.id", index=True)

    # Entity identification (dynamic - not enum-based)
    connector_type: ConnectorType = Field(index=True)
    entity_type: str = Field(max_length=100, index=True)  # e.g., "invoice", "customer", "profit_loss"
    external_id: Optional[str] = Field(default=None, max_length=255, index=True)  # ID from external system

    # Raw data storage
    raw_data: dict = Field(sa_column=Column(JSON))  # Original JSON from API

    # Processing status
    is_processed: bool = Field(default=False, index=True)
    processed_at: Optional[datetime] = Field(default=None)

    # Sync tracking
    sync_log_id: Optional[str] = Field(default=None, foreign_key="connector_sync_logs.id", index=True)
    synced_at: datetime = Field(default_factory=datetime.utcnow)

    # For delta syncs - track when record was last modified in source
    external_updated_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConnectorChunk(SQLModel, table=True):
    """
    Stores processed chunks from connector data.
    Parallel to DocumentChunk but for connector sources.
    Used for RAG retrieval.
    """
    __tablename__ = "connector_chunks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    company_id: str = Field(foreign_key="companies.id", index=True)

    # Source tracking
    connector_config_id: str = Field(foreign_key="connector_configs.id", index=True)
    connector_type: ConnectorType = Field(index=True)
    raw_data_id: Optional[str] = Field(default=None, foreign_key="connector_raw_data.id", index=True)

    # Entity reference (dynamic - not enum-based)
    entity_type: str = Field(max_length=100, index=True)  # e.g., "invoice", "customer"
    entity_id: Optional[str] = Field(default=None, max_length=255)  # External system ID
    entity_name: Optional[str] = Field(default=None, max_length=500)  # Human-readable name

    # Chunk content (generated by LLM)
    content: str = Field(sa_column=Column(Text))  # Natural language content
    summary: str = Field(sa_column=Column(Text))  # Short summary for embedding

    # Classification (detected by LLM)
    pillar: str = Field(max_length=100, index=True)  # BDE pillar
    secondary_pillar: Optional[str] = Field(default=None, max_length=100)

    # Chunk metadata
    chunk_type: str = Field(default="connector_data", max_length=50)  # "connector_data", "aggregated_summary"
    confidence_score: Optional[float] = Field(default=None)  # LLM confidence in classification

    # Additional metadata
    metadata_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    # e.g., {"period": "Q4 2025", "amount": 15000, "customer": "Acme Corp"}

    # Vector embedding for RAG (3072 dimensions for text-embedding-3-large)
    embedding: Optional[list] = Field(default=None, sa_column=Column(Vector(3072)))

    # Temporal tracking
    data_as_of: Optional[datetime] = Field(default=None)  # When this data represents
    synced_at: datetime = Field(default_factory=datetime.utcnow)  # When synced from source
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Source type for metrics - to track where metrics came from
class MetricSourceType(str, Enum):
    """Source type for company metrics"""
    DOCUMENT = "document"
    CONNECTOR = "connector"
    MANUAL = "manual"  # Analyst override


# Default priority for metric sources (higher = more trusted)
METRIC_SOURCE_PRIORITY = {
    MetricSourceType.MANUAL: 200,  # Analyst override always wins
    MetricSourceType.CONNECTOR: 100,  # Direct from source system
    MetricSourceType.DOCUMENT: 50,  # Extracted from documents
}
