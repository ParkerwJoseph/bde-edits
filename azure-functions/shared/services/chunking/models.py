"""
Data models for the unified chunking service.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum


# Type alias for progress callback function
# Signature: (current_page: int, total_pages: int, step_name: str) -> None
ProgressCallback = Callable[[int, int, str], None]


class SourceType(str, Enum):
    """Source type for chunking input"""
    DOCUMENT = "document"
    CONNECTOR = "connector"


@dataclass
class ChunkInput:
    """
    Unified input for chunking operations.

    Supports both document and connector sources with source-specific fields.
    """
    source_type: SourceType
    tenant_id: str
    company_id: str

    # Document-specific fields
    document_id: Optional[str] = None
    pages: Optional[List[dict]] = None  # {'page_number', 'image_base64'/'text_content'}
    document_filename: Optional[str] = None

    # Connector-specific fields
    connector_config_id: Optional[str] = None
    connector_type: Optional[str] = None  # 'quickbooks', 'salesforce', etc.
    entity_type: Optional[str] = None  # 'invoice', 'customer', 'profit_loss', etc.
    raw_records: Optional[List[dict]] = None  # List of raw data records


@dataclass
class ChunkOutput:
    """
    Unified output from chunking operations.

    Contains all fields needed for both DocumentChunk and ConnectorChunk storage.
    """
    content: str
    summary: str
    pillar: str  # BDEPillar value
    chunk_type: str
    confidence_score: float
    metadata: Dict[str, Any]
    source_type: SourceType

    # Embedding (generated after LLM processing)
    embedding: Optional[List[float]] = None

    # Document-specific fields
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    previous_context: Optional[str] = None

    # Connector-specific fields
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    entity_ids: Optional[List[str]] = None  # Source record IDs for aggregated chunks
    aggregation_type: Optional[str] = None  # 'summary', 'trend', 'segment', 'comparison'
    data_as_of: Optional[datetime] = None
    connector_type: Optional[str] = None


@dataclass
class ChunkingResult:
    """Result from a chunking operation"""
    chunks: List[ChunkOutput]
    overview: Dict[str, Any]
    usage_stats: Dict[str, int]


@dataclass
class NormalizedInput:
    """
    Normalized input for chunking strategies.

    Adapters convert source-specific input to this common format.
    """
    content_units: List[Dict[str, Any]]  # Pages or record groups
    context: Dict[str, Any]  # Metadata for prompt generation
    source_info: Dict[str, Any]  # Source tracking info (IDs, etc.)


# Entity-specific aggregation configuration
ENTITY_AGGREGATION_CONFIG = {
    'invoice': {
        'strategy': 'temporal_summary',
        'group_by': 'month',
        'max_chunks': 15,
        'chunk_types': ['revenue_summary', 'customer_concentration', 'trend_analysis'],
    },
    'customer': {
        'strategy': 'segment_summary',
        'group_by': 'segment',
        'max_chunks': 8,
        'chunk_types': ['customer_base', 'segment_analysis', 'health_indicators'],
    },
    'profit_loss': {
        'strategy': 'period_analysis',
        'group_by': 'period',
        'max_chunks': 8,
        'chunk_types': ['financial_performance', 'expense_analysis', 'margin_trends'],
    },
    'balance_sheet': {
        'strategy': 'snapshot_analysis',
        'group_by': 'date',
        'max_chunks': 6,
        'chunk_types': ['asset_summary', 'liability_summary', 'equity_analysis'],
    },
    'vendor': {
        'strategy': 'category_summary',
        'group_by': 'category',
        'max_chunks': 10,
        'chunk_types': ['vendor_summary', 'concentration_analysis'],
    },
    'bill': {
        'strategy': 'temporal_summary',
        'group_by': 'month',
        'max_chunks': 12,
        'chunk_types': ['expense_summary', 'vendor_distribution'],
    },
    'payment': {
        'strategy': 'temporal_summary',
        'group_by': 'month',
        'max_chunks': 8,
        'chunk_types': ['payment_summary', 'payment_patterns'],
    },
    'item': {
        'strategy': 'category_summary',
        'group_by': 'type',
        'max_chunks': 6,
        'chunk_types': ['product_catalog', 'pricing_analysis'],
    },
    'account': {
        'strategy': 'category_summary',
        'group_by': 'account_type',
        'max_chunks': 8,
        'chunk_types': ['account_structure', 'balance_summary'],
    },
    'employee': {
        'strategy': 'segment_summary',
        'group_by': 'department',
        'max_chunks': 6,
        'chunk_types': ['workforce_summary', 'team_structure'],
    },
    # Reports - typically single records, processed as summaries
    'cash_flow': {
        'strategy': 'report_analysis',
        'group_by': 'period',
        'max_chunks': 6,
        'chunk_types': ['cash_flow_summary', 'liquidity_analysis'],
    },
    'ar_aging': {
        'strategy': 'report_analysis',
        'group_by': 'aging_bucket',
        'max_chunks': 6,
        'chunk_types': ['receivables_summary', 'collection_risk'],
    },
    'ap_aging': {
        'strategy': 'report_analysis',
        'group_by': 'aging_bucket',
        'max_chunks': 6,
        'chunk_types': ['payables_summary', 'payment_obligations'],
    },
    'customer_income': {
        'strategy': 'report_analysis',
        'group_by': 'customer_segment',
        'max_chunks': 8,
        'chunk_types': ['revenue_concentration', 'customer_contribution'],
    },
}

# Default config for unknown entity types
DEFAULT_AGGREGATION_CONFIG = {
    'strategy': 'general_summary',
    'group_by': 'batch',
    'max_chunks': 10,
    'chunk_types': ['general_summary'],
}
