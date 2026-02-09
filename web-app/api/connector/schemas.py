"""Pydantic schemas for connector API endpoints"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ConnectorTypeEnum(str, Enum):
    """Supported connector types"""
    QUICKBOOKS = "quickbooks"
    CARBONVOICE = "carbonvoice"


class ConnectorStatusEnum(str, Enum):
    """Connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
    ERROR = "error"


class SyncStatusEnum(str, Enum):
    """Sync operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Entity Discovery Schemas
# ============================================================================

class EntityInfo(BaseModel):
    """Information about an available entity"""
    entity_key: str
    display_name: str
    description: str
    is_report: bool = False  # QuickBooks-specific, default False for other connectors
    default_enabled: bool
    pillar_hint: str
    record_count: Optional[int] = None
    is_available: bool = False
    error: Optional[str] = None


class DiscoverEntitiesResponse(BaseModel):
    """Response for entity discovery"""
    entities: List[EntityInfo]
    company_info: Optional[Dict[str, Any]] = None


# ============================================================================
# OAuth Schemas
# ============================================================================

class OAuthStartResponse(BaseModel):
    """Response for starting OAuth flow"""
    authorization_url: str
    state: str  # Client should store this for CSRF verification


class OAuthCallbackRequest(BaseModel):
    """Request body for OAuth callback"""
    code: str
    state: str
    realm_id: str  # QuickBooks company ID


class OAuthCallbackResponse(BaseModel):
    """Response for OAuth callback"""
    success: bool
    connector_config_id: Optional[str] = None
    company_name: Optional[str] = None
    message: str


# ============================================================================
# Connector Config Schemas
# ============================================================================

class ConnectorConfigBase(BaseModel):
    """Base connector config fields"""
    connector_type: ConnectorTypeEnum
    enabled_entities: Optional[List[str]] = None
    sync_settings: Optional[Dict[str, Any]] = None


class ConnectorConfigCreate(ConnectorConfigBase):
    """Create connector config"""
    company_id: str


class ConnectorConfigUpdate(BaseModel):
    """Update connector config"""
    enabled_entities: Optional[List[str]] = None
    sync_settings: Optional[Dict[str, Any]] = None


class ConnectorConfigResponse(BaseModel):
    """Connector config response"""
    id: str
    tenant_id: str
    company_id: str
    connector_type: ConnectorTypeEnum
    connector_status: ConnectorStatusEnum
    external_company_id: Optional[str] = None
    external_company_name: Optional[str] = None
    available_entities: Optional[Dict[str, Any]] = None
    enabled_entities: Optional[List[str]] = None
    sync_settings: Optional[Dict[str, Any]] = None
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[SyncStatusEnum] = None
    last_sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('connector_type', mode='before')
    @classmethod
    def normalize_connector_type(cls, v):
        """Handle both enum objects and string values (case-insensitive)"""
        if hasattr(v, 'value'):
            return v.value
        if isinstance(v, str):
            # Handle both enum names (QUICKBOOKS) and values (quickbooks)
            return v.lower()
        return v

    @field_validator('connector_status', mode='before')
    @classmethod
    def normalize_connector_status(cls, v):
        """Handle both enum objects and string values (case-insensitive)"""
        if hasattr(v, 'value'):
            return v.value
        if isinstance(v, str):
            # Handle both enum names (CONNECTED) and values (connected)
            v_lower = v.lower()
            # Map enum names to values if needed
            name_to_value = {
                'connected': 'connected',
                'disconnected': 'disconnected',
                'expired': 'expired',
                'error': 'error',
            }
            return name_to_value.get(v_lower, v_lower)
        return v

    @field_validator('last_sync_status', mode='before')
    @classmethod
    def normalize_last_sync_status(cls, v):
        """Handle both enum objects and string values (case-insensitive)"""
        if v is None:
            return None
        if hasattr(v, 'value'):
            return v.value
        if isinstance(v, str):
            return v.lower()
        return v

    class Config:
        from_attributes = True


class ConnectorConfigListResponse(BaseModel):
    """List of connector configs"""
    connectors: List[ConnectorConfigResponse]
    total: int


# ============================================================================
# Sync Schemas
# ============================================================================

class SyncRequest(BaseModel):
    """Request to start a sync"""
    entities: Optional[List[str]] = None  # None = use enabled_entities from config
    full_sync: bool = True  # False = delta sync since last sync


class SyncStartResponse(BaseModel):
    """Response for starting sync"""
    sync_log_id: str
    status: SyncStatusEnum
    message: str


class SyncStatusResponse(BaseModel):
    """Response for sync status"""
    id: str
    status: SyncStatusEnum
    sync_type: str
    entities_requested: Optional[List[str]] = None
    entities_completed: Optional[List[str]] = None
    total_records_fetched: int = 0
    total_records_processed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SyncLogResponse(BaseModel):
    """Sync log entry"""
    id: str
    connector_config_id: str
    sync_status: SyncStatusEnum
    sync_type: str
    entities_requested: Optional[List[str]] = None
    entities_completed: Optional[List[str]] = None
    total_records_fetched: int
    total_records_processed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class SyncLogListResponse(BaseModel):
    """List of sync logs"""
    sync_logs: List[SyncLogResponse]
    total: int


# ============================================================================
# Ingestion Schemas
# ============================================================================

class IngestionRequest(BaseModel):
    """Request to process raw data"""
    entity_types: Optional[List[str]] = None  # None = process all unprocessed


class IngestionResponse(BaseModel):
    """Response for ingestion"""
    connector_config_id: str
    status: str = "queued"
    message: str = "Ingestion queued for processing"


class IngestionWebhookPayload(BaseModel):
    """Webhook payload from Azure Function for ingestion progress"""
    connector_config_id: str
    status: str  # "processing", "completed", "failed"
    step: int
    step_name: str
    progress: int
    current_entity: Optional[str] = None
    entities_completed: Optional[List[str]] = None
    records_processed: Optional[int] = None
    chunks_created: Optional[int] = None
    error_message: Optional[str] = None


# ============================================================================
# Supported Connectors Schemas
# ============================================================================

class SupportedConnectorInfo(BaseModel):
    """Info about a supported connector type"""
    connector_type: str
    display_name: str
    description: str
    is_configured: bool  # Whether credentials are configured in env


class SupportedConnectorsResponse(BaseModel):
    """List of supported connectors"""
    connectors: List[SupportedConnectorInfo]
