"""
Unified Chunking Service for documents and connectors.

This package provides a single, consistent interface for chunking content
from any source (documents, QuickBooks, future connectors) with high quality
and consistent output format.

Usage:
    from services.chunking import get_chunking_service, ChunkInput, SourceType

    service = get_chunking_service()
    result = await service.process(ChunkInput(
        source_type=SourceType.CONNECTOR,
        tenant_id="...",
        company_id="...",
        connector_type="quickbooks",
        entity_type="invoice",
        raw_records=[...]
    ))
"""
from services.chunking.models import (
    SourceType,
    ChunkInput,
    ChunkOutput,
    ChunkingResult,
    NormalizedInput,
    ENTITY_AGGREGATION_CONFIG,
    DEFAULT_AGGREGATION_CONFIG,
)
from services.chunking.chunking_service import (
    ChunkingService,
    get_chunking_service,
)

__all__ = [
    # Main service
    "ChunkingService",
    "get_chunking_service",
    # Models
    "SourceType",
    "ChunkInput",
    "ChunkOutput",
    "ChunkingResult",
    "NormalizedInput",
    # Config
    "ENTITY_AGGREGATION_CONFIG",
    "DEFAULT_AGGREGATION_CONFIG",
]
