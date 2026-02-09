"""
QuickBooks Ingestion Service.
Processes raw QuickBooks data into chunks using the unified ChunkingService.

This service now uses aggregation-based chunking:
- 10,000 invoices -> ~15 insight chunks (not 10,000)
- Groups records by time period/category
- Creates summary, trend, and segment chunks
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlmodel import Session, select

from database.models.connector import (
    ConnectorConfig,
    ConnectorRawData,
    ConnectorChunk,
    ConnectorType,
)
from services.chunking import (
    get_chunking_service,
    ChunkInput,
    SourceType,
)
from services.chunking.adapters.connector_adapter import ConnectorAdapter
from utils.logger import get_logger

logger = get_logger(__name__)


class QuickBooksIngestionService:
    """
    Service for processing raw QuickBooks data into searchable chunks.

    Uses the unified ChunkingService with aggregation-based chunking:
    - Groups records by time period (month/quarter)
    - Creates insight chunks instead of 1:1 record chunks
    - Limits total chunks based on entity type configuration
    """

    def __init__(self, session: Session):
        """
        Initialize ingestion service.

        Args:
            session: Database session
        """
        self.session = session
        self.chunking_service = get_chunking_service()
        self.connector_adapter = ConnectorAdapter()

    async def process_raw_data(
        self,
        connector_config_id: str,
        entity_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process unprocessed raw data into aggregated chunks.

        Unlike the old approach that created 1 chunk per record,
        this uses aggregation-based chunking to create meaningful
        insight chunks.

        Args:
            connector_config_id: ID of the ConnectorConfig
            entity_types: Specific entity types to process (None = all)

        Returns:
            Dict with processing results including chunks_created count
        """
        logger.info(f"[QuickBooksIngestion] Starting ingestion for connector {connector_config_id}")
        logger.info(f"[QuickBooksIngestion] Entity types filter: {entity_types}")

        # Get connector config
        config = self.session.get(ConnectorConfig, connector_config_id)
        if not config:
            logger.error(f"[QuickBooksIngestion] ConnectorConfig not found: {connector_config_id}")
            raise ValueError(f"ConnectorConfig not found: {connector_config_id}")

        logger.info(f"[QuickBooksIngestion] Found connector for company: {config.external_company_name}")

        # Query unprocessed raw data
        query = select(ConnectorRawData).where(
            ConnectorRawData.connector_config_id == connector_config_id,
            ConnectorRawData.is_processed == False,
        )

        if entity_types:
            query = query.where(ConnectorRawData.entity_type.in_(entity_types))

        raw_records = list(self.session.exec(query).all())

        if not raw_records:
            logger.info(f"[QuickBooksIngestion] No unprocessed records found for config {connector_config_id}")
            return {"processed": 0, "chunks_created": 0, "entity_stats": {}}

        logger.info(f"[QuickBooksIngestion] Found {len(raw_records)} unprocessed raw records to process")

        # Group by entity type
        records_by_type: Dict[str, List[ConnectorRawData]] = {}
        for record in raw_records:
            if record.entity_type not in records_by_type:
                records_by_type[record.entity_type] = []
            records_by_type[record.entity_type].append(record)

        logger.info(f"[QuickBooksIngestion] Records grouped by entity type: {{{', '.join([f'{k}: {len(v)}' for k, v in records_by_type.items()])}}}")

        total_processed = 0
        total_chunks = 0
        entity_stats = {}

        # Process each entity type using unified ChunkingService
        for entity_type, records in records_by_type.items():
            logger.info(f"[QuickBooksIngestion] === Processing entity type: {entity_type} ({len(records)} records) ===")

            try:
                # Convert raw records to raw_data list
                raw_data_list = [record.raw_data for record in records]

                # Create ChunkInput for the chunking service
                chunk_input = ChunkInput(
                    source_type=SourceType.CONNECTOR,
                    tenant_id=config.tenant_id,
                    company_id=config.company_id,
                    connector_config_id=config.id,
                    connector_type="quickbooks",
                    entity_type=entity_type,
                    raw_records=raw_data_list,
                )

                # Process through unified chunking service
                result = await self.chunking_service.process(chunk_input)

                logger.info(
                    f"[QuickBooksIngestion] ChunkingService returned {len(result.chunks)} chunks "
                    f"for {len(records)} {entity_type} records"
                )

                # Convert ChunkOutput to ConnectorChunk and save
                chunks_created = 0
                for chunk_output in result.chunks:
                    connector_chunk = ConnectorChunk(
                        tenant_id=config.tenant_id,
                        company_id=config.company_id,
                        connector_config_id=config.id,
                        connector_type=ConnectorType.QUICKBOOKS,
                        entity_type=chunk_output.entity_type or entity_type,
                        entity_name=chunk_output.entity_name,
                        content=chunk_output.content,
                        summary=chunk_output.summary,
                        pillar=chunk_output.pillar,
                        chunk_type=chunk_output.chunk_type or "aggregated_summary",
                        confidence_score=chunk_output.confidence_score,
                        metadata_json=chunk_output.metadata,
                        embedding=chunk_output.embedding,
                        data_as_of=chunk_output.data_as_of,
                        synced_at=datetime.utcnow(),
                    )
                    self.session.add(connector_chunk)
                    chunks_created += 1

                # Mark all records as processed
                for record in records:
                    record.is_processed = True
                    record.processed_at = datetime.utcnow()
                    self.session.add(record)

                self.session.commit()

                total_processed += len(records)
                total_chunks += chunks_created

                entity_stats[entity_type] = {
                    "records_processed": len(records),
                    "chunks_created": chunks_created,
                    "usage_stats": result.usage_stats,
                }

                logger.info(
                    f"[QuickBooksIngestion] {entity_type} complete: "
                    f"{len(records)} records -> {chunks_created} chunks "
                    f"(ratio: {len(records)/chunks_created:.1f}:1)"
                    if chunks_created > 0 else
                    f"[QuickBooksIngestion] {entity_type} complete: {len(records)} records -> 0 chunks"
                )

            except Exception as e:
                logger.error(f"[QuickBooksIngestion] Error processing {entity_type}: {e}", exc_info=True)
                entity_stats[entity_type] = {
                    "records_processed": 0,
                    "chunks_created": 0,
                    "error": str(e),
                }
                # Continue with next entity type

        logger.info(
            f"[QuickBooksIngestion] === INGESTION COMPLETE === "
            f"Total: {total_processed} records processed, {total_chunks} chunks created"
        )

        return {
            "processed": total_processed,
            "chunks_created": total_chunks,
            "entity_stats": entity_stats,
        }

    async def reprocess_entity(
        self,
        connector_config_id: str,
        entity_type: str,
    ) -> Dict[str, Any]:
        """
        Reprocess all data for a specific entity type.
        Deletes existing chunks and reprocesses from raw data.

        Args:
            connector_config_id: ID of the ConnectorConfig
            entity_type: Entity type to reprocess

        Returns:
            Dict with processing results
        """
        # Delete existing chunks for this entity type
        existing_chunks = self.session.exec(
            select(ConnectorChunk).where(
                ConnectorChunk.connector_config_id == connector_config_id,
                ConnectorChunk.entity_type == entity_type,
            )
        ).all()

        for chunk in existing_chunks:
            self.session.delete(chunk)

        # Mark raw data as unprocessed
        raw_records = self.session.exec(
            select(ConnectorRawData).where(
                ConnectorRawData.connector_config_id == connector_config_id,
                ConnectorRawData.entity_type == entity_type,
            )
        ).all()

        for record in raw_records:
            record.is_processed = False
            record.processed_at = None
            self.session.add(record)

        self.session.commit()

        logger.info(
            f"[QuickBooksIngestion] Reset {len(existing_chunks)} chunks, "
            f"{len(raw_records)} raw records for {entity_type}"
        )

        # Process the raw data
        return await self.process_raw_data(
            connector_config_id=connector_config_id,
            entity_types=[entity_type],
        )


def get_quickbooks_ingestion_service(session: Session) -> QuickBooksIngestionService:
    """Factory function to create QuickBooksIngestionService"""
    return QuickBooksIngestionService(session)
