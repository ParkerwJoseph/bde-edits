"""
QuickBooks Sync Service.
Handles fetching data from QuickBooks and storing it in the raw data table.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlmodel import Session, select

from database.models.connector import (
    ConnectorConfig,
    ConnectorRawData,
    ConnectorSyncLog,
    ConnectorChunk,
    ConnectorStatus,
    SyncStatus,
    ConnectorType,
)
from services.connectors.quickbooks.client import QuickBooksConnector
from utils.logger import get_logger

logger = get_logger(__name__)


class QuickBooksSyncService:
    """
    Service for syncing data from QuickBooks to the raw data table.
    """

    def __init__(self, session: Session):
        """
        Initialize sync service.

        Args:
            session: Database session
        """
        self.session = session

    async def sync_company(
        self,
        connector_config_id: str,
        entities: Optional[List[str]] = None,
        full_sync: bool = True,
        triggered_by: Optional[str] = None,
    ) -> ConnectorSyncLog:
        """
        Sync data from QuickBooks for a company.

        Args:
            connector_config_id: ID of the ConnectorConfig record
            entities: List of entity keys to sync (None = use enabled_entities from config)
            full_sync: If True, fetch all data. If False, only fetch changes since last sync.
            triggered_by: User ID who triggered the sync (None if scheduled)

        Returns:
            ConnectorSyncLog record with sync results
        """
        logger.info(f"[QuickBooksSync] === STARTING {'FULL' if full_sync else 'DELTA'} SYNC ===")
        logger.info(f"[QuickBooksSync] Connector config ID: {connector_config_id}")
        logger.info(f"[QuickBooksSync] Requested entities: {entities}")
        logger.info(f"[QuickBooksSync] Triggered by: {triggered_by}")

        # Get connector config
        config = self.session.get(ConnectorConfig, connector_config_id)
        if not config:
            logger.error(f"[QuickBooksSync] ConnectorConfig not found: {connector_config_id}")
            raise ValueError(f"ConnectorConfig not found: {connector_config_id}")

        if config.connector_type != ConnectorType.QUICKBOOKS:
            logger.error(f"[QuickBooksSync] Wrong connector type: {config.connector_type}")
            raise ValueError(f"Expected QuickBooks connector, got: {config.connector_type}")

        logger.info(f"[QuickBooksSync] Company: {config.external_company_name} (QB ID: {config.external_company_id})")

        # Determine which entities to sync
        entities_to_sync = entities or config.enabled_entities or []
        if not entities_to_sync:
            logger.error("[QuickBooksSync] No entities specified for sync")
            raise ValueError("No entities specified for sync")

        logger.info(f"[QuickBooksSync] Entities to sync: {entities_to_sync}")

        # Create sync log
        sync_log = ConnectorSyncLog(
            connector_config_id=connector_config_id,
            tenant_id=config.tenant_id,
            company_id=config.company_id,
            sync_status=SyncStatus.IN_PROGRESS,
            sync_type="full" if full_sync else "delta",
            entities_requested=entities_to_sync,
            entities_completed=[],
            total_records_fetched=0,
            total_records_processed=0,
            triggered_by=triggered_by,
        )
        self.session.add(sync_log)
        self.session.commit()
        self.session.refresh(sync_log)
        logger.info(f"[QuickBooksSync] Created sync log: {sync_log.id}")

        # Update config status
        config.last_sync_status = SyncStatus.IN_PROGRESS
        self.session.add(config)
        self.session.commit()

        try:
            # Initialize QuickBooks connector
            connector = QuickBooksConnector(config)
            logger.info(f"[QuickBooksSync] QuickBooks connector initialized (environment: {connector.environment})")

            # Refresh token if needed
            if config.needs_token_refresh():
                logger.info("[QuickBooksSync] Token needs refresh, refreshing...")
                await self._refresh_token(config, connector)
            else:
                logger.info("[QuickBooksSync] Token is valid, no refresh needed")

            # Get last sync time for delta syncs
            since = None if full_sync else config.last_sync_at
            if since:
                logger.info(f"[QuickBooksSync] Delta sync since: {since.isoformat()}")
            else:
                logger.info("[QuickBooksSync] Full sync (no since filter)")

            # Sync each entity
            completed_entities = []
            total_fetched = 0
            total_processed = 0

            for i, entity_key in enumerate(entities_to_sync, 1):
                logger.info(f"[QuickBooksSync] --- Syncing entity {i}/{len(entities_to_sync)}: {entity_key} ---")
                try:
                    fetched, processed = await self._sync_entity(
                        connector=connector,
                        config=config,
                        sync_log=sync_log,
                        entity_key=entity_key,
                        since=since,
                        full_sync=full_sync,
                    )
                    completed_entities.append(entity_key)
                    total_fetched += fetched
                    total_processed += processed

                    logger.info(f"[QuickBooksSync] Entity {entity_key} complete: {fetched} fetched, {processed} stored")
                    logger.info(f"[QuickBooksSync] Running totals: {total_fetched} fetched, {total_processed} stored")

                    # Update sync log progress
                    sync_log.entities_completed = completed_entities
                    sync_log.total_records_fetched = total_fetched
                    sync_log.total_records_processed = total_processed
                    self.session.add(sync_log)
                    self.session.commit()

                except Exception as e:
                    logger.error(f"[QuickBooksSync] Error syncing entity {entity_key}: {e}", exc_info=True)
                    # Continue with other entities

            # Mark sync as completed
            sync_log.sync_status = SyncStatus.COMPLETED
            sync_log.completed_at = datetime.utcnow()
            self.session.add(sync_log)

            # Update config
            config.last_sync_at = datetime.utcnow()
            config.last_sync_status = SyncStatus.COMPLETED
            config.last_sync_error = None
            self.session.add(config)

            self.session.commit()
            self.session.refresh(sync_log)

            logger.info(f"[QuickBooksSync] === SYNC COMPLETE ===")
            logger.info(f"[QuickBooksSync] Entities completed: {completed_entities}")
            logger.info(f"[QuickBooksSync] Total records fetched: {total_fetched}")
            logger.info(f"[QuickBooksSync] Total records stored: {total_processed}")

            return sync_log

        except Exception as e:
            logger.error(f"[QuickBooksSync] === SYNC FAILED ===")
            logger.error(f"[QuickBooksSync] Error: {e}", exc_info=True)

            # Mark sync as failed
            sync_log.sync_status = SyncStatus.FAILED
            sync_log.completed_at = datetime.utcnow()
            sync_log.error_message = str(e)
            self.session.add(sync_log)

            # Update config
            config.last_sync_status = SyncStatus.FAILED
            config.last_sync_error = str(e)
            self.session.add(config)

            self.session.commit()
            self.session.refresh(sync_log)

            raise

    async def _refresh_token(self, config: ConnectorConfig, connector: QuickBooksConnector):
        """Refresh the OAuth token and update config"""
        try:
            token_data = await connector.refresh_access_token()

            config.access_token = token_data.get("access_token")
            config.refresh_token = token_data.get("refresh_token", config.refresh_token)
            config.token_expiry = datetime.utcnow() + \
                                  __import__('datetime').timedelta(seconds=token_data.get("expires_in", 3600))
            config.connector_status = ConnectorStatus.CONNECTED

            self.session.add(config)
            self.session.commit()

            # Update connector's config reference
            connector.config = config

            logger.info(f"[QuickBooksSync] Refreshed token for config {config.id}")

        except Exception as e:
            logger.error(f"[QuickBooksSync] Failed to refresh token: {e}")
            config.connector_status = ConnectorStatus.EXPIRED
            self.session.add(config)
            self.session.commit()
            raise

    async def _sync_entity(
        self,
        connector: QuickBooksConnector,
        config: ConnectorConfig,
        sync_log: ConnectorSyncLog,
        entity_key: str,
        since: Optional[datetime],
        full_sync: bool,
    ) -> tuple[int, int]:
        """
        Sync a single entity type.

        Returns:
            Tuple of (records_fetched, records_stored)
        """
        logger.info(f"[QuickBooksSync] _sync_entity starting for: {entity_key}")
        logger.info(f"[QuickBooksSync] Full sync: {full_sync}, Since: {since}")

        # For full sync, delete existing raw data for this entity
        if full_sync:
            logger.info(f"[QuickBooksSync] Full sync requested, deleting existing data for {entity_key}")
            await self._delete_entity_raw_data(config, entity_key)

        # Check if this entity has ever been synced before
        # If not, do a full sync for this entity even if delta sync was requested
        entity_since = since
        if not full_sync and since:
            existing_record = self.session.exec(
                select(ConnectorRawData)
                .where(ConnectorRawData.connector_config_id == config.id)
                .where(ConnectorRawData.entity_type == entity_key)
            ).first()

            if not existing_record:
                # Entity has never been synced, do full sync for this entity
                logger.info(f"[QuickBooksSync] Entity {entity_key} has NO existing records - switching to full sync for this entity")
                entity_since = None
            else:
                logger.info(f"[QuickBooksSync] Entity {entity_key} has existing records - using delta sync since {since}")

        # Fetch data from QuickBooks
        logger.info(f"[QuickBooksSync] Fetching {entity_key} from QuickBooks API...")
        if entity_since:
            logger.info(f"[QuickBooksSync] Query filter: records modified after {entity_since.isoformat()}")
        else:
            logger.info(f"[QuickBooksSync] Query filter: ALL records (no date filter)")

        records = await connector.fetch_all_entity_data(
            entity_key=entity_key,
            since=entity_since,
        )

        records_fetched = len(records)
        logger.info(f"[QuickBooksSync] QuickBooks API returned {records_fetched} {entity_key} records")

        records_stored = 0
        records_updated = 0
        records_created = 0

        # Store each record
        for record in records:
            external_id = connector.get_entity_external_id(entity_key, record)
            external_updated_at = connector.get_entity_updated_at(entity_key, record)

            # Check if record already exists (for delta syncs)
            existing = None
            if not full_sync and external_id:
                existing = self.session.exec(
                    select(ConnectorRawData)
                    .where(ConnectorRawData.connector_config_id == config.id)
                    .where(ConnectorRawData.entity_type == entity_key)
                    .where(ConnectorRawData.external_id == external_id)
                ).first()

            if existing:
                # Update existing record
                records_updated += 1
                existing.raw_data = record
                existing.external_updated_at = external_updated_at
                existing.synced_at = datetime.utcnow()
                existing.is_processed = False  # Mark for reprocessing
                existing.updated_at = datetime.utcnow()
                self.session.add(existing)
            else:
                # Create new record
                records_created += 1
                raw_data = ConnectorRawData(
                    connector_config_id=config.id,
                    tenant_id=config.tenant_id,
                    company_id=config.company_id,
                    connector_type=ConnectorType.QUICKBOOKS,
                    entity_type=entity_key,
                    external_id=external_id,
                    raw_data=record,
                    is_processed=False,
                    sync_log_id=sync_log.id,
                    external_updated_at=external_updated_at,
                )
                self.session.add(raw_data)

            records_stored += 1

        self.session.commit()

        logger.info(f"[QuickBooksSync] Entity {entity_key} sync complete:")
        logger.info(f"[QuickBooksSync]   - Records fetched from API: {records_fetched}")
        logger.info(f"[QuickBooksSync]   - New records created: {records_created}")
        logger.info(f"[QuickBooksSync]   - Existing records updated: {records_updated}")
        logger.info(f"[QuickBooksSync]   - Total records stored: {records_stored}")
        return records_fetched, records_stored

    async def _delete_entity_raw_data(self, config: ConnectorConfig, entity_key: str):
        """Delete existing raw data for an entity (for full sync)"""
        # First, delete related chunks that reference this entity's raw data
        existing_chunks = self.session.exec(
            select(ConnectorChunk)
            .where(ConnectorChunk.connector_config_id == config.id)
            .where(ConnectorChunk.entity_type == entity_key)
        ).all()

        for chunk in existing_chunks:
            self.session.delete(chunk)

        if existing_chunks:
            self.session.commit()
            logger.info(f"[QuickBooksSync] Deleted {len(existing_chunks)} existing {entity_key} chunks")

        # Now delete raw data records
        existing_records = self.session.exec(
            select(ConnectorRawData)
            .where(ConnectorRawData.connector_config_id == config.id)
            .where(ConnectorRawData.entity_type == entity_key)
        ).all()

        for record in existing_records:
            self.session.delete(record)

        self.session.commit()
        logger.info(f"[QuickBooksSync] Deleted {len(existing_records)} existing {entity_key} records")

    async def get_sync_status(self, sync_log_id: str) -> Dict[str, Any]:
        """
        Get status of a sync operation.

        Args:
            sync_log_id: ID of the ConnectorSyncLog

        Returns:
            Dict with sync status information
        """
        sync_log = self.session.get(ConnectorSyncLog, sync_log_id)
        if not sync_log:
            raise ValueError(f"SyncLog not found: {sync_log_id}")

        return {
            "id": sync_log.id,
            "status": sync_log.sync_status.value,
            "sync_type": sync_log.sync_type,
            "entities_requested": sync_log.entities_requested,
            "entities_completed": sync_log.entities_completed,
            "total_records_fetched": sync_log.total_records_fetched,
            "total_records_processed": sync_log.total_records_processed,
            "started_at": sync_log.started_at.isoformat() if sync_log.started_at else None,
            "completed_at": sync_log.completed_at.isoformat() if sync_log.completed_at else None,
            "error_message": sync_log.error_message,
        }


def get_quickbooks_sync_service(session: Session) -> QuickBooksSyncService:
    """Factory function to create QuickBooksSyncService"""
    return QuickBooksSyncService(session)
