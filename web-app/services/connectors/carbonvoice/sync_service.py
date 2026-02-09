"""
Carbon Voice Sync Service.
Handles fetching and storing data from Carbon Voice.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, select

from database.models.connector import (
    ConnectorConfig,
    ConnectorSyncLog,
    ConnectorRawData,
    ConnectorType,
    ConnectorStatus,
    SyncStatus,
)
from services.connectors.carbonvoice.client import (
    CarbonVoiceConnector,
    CARBONVOICE_ENTITY_MAP,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class CarbonVoiceSyncService:
    """
    Service for syncing Carbon Voice data to the database.
    """

    def __init__(self, session: Session):
        self.session = session

    async def sync_company(
        self,
        connector_config_id: str,
        entities: Optional[List[str]] = None,
        full_sync: bool = True,
        triggered_by: Optional[str] = None,
    ) -> ConnectorSyncLog:
        """
        Sync Carbon Voice data for a company.

        Args:
            connector_config_id: ID of the connector config
            entities: List of entity types to sync (None = all enabled)
            full_sync: If True, fetch all data. If False, delta sync.
            triggered_by: User ID who triggered the sync

        Returns:
            ConnectorSyncLog record
        """
        # Get connector config
        config = self.session.get(ConnectorConfig, connector_config_id)
        if not config:
            raise ValueError(f"Connector config not found: {connector_config_id}")

        # Determine which entities to sync
        if entities is None:
            entities = config.enabled_entities or ["workspace", "channel", "message"]

        # Create sync log
        sync_log = ConnectorSyncLog(
            connector_config_id=connector_config_id,
            tenant_id=config.tenant_id,
            company_id=config.company_id,
            sync_status=SyncStatus.IN_PROGRESS,
            sync_type="full" if full_sync else "delta",
            entities_requested=entities,
            entities_completed=[],
            total_records_fetched=0,
            total_records_processed=0,
            triggered_by=triggered_by,
        )
        self.session.add(sync_log)
        self.session.commit()
        self.session.refresh(sync_log)

        # Update config status
        config.last_sync_status = SyncStatus.IN_PROGRESS
        self.session.add(config)
        self.session.commit()

        # Initialize connector
        connector = CarbonVoiceConnector(config)

        try:
            # Refresh token if needed
            if config.needs_token_refresh():
                logger.info(f"[CarbonVoice] Refreshing token for config {connector_config_id}")
                token_data = await connector.refresh_access_token()
                config.access_token = token_data.get("access_token")
                config.refresh_token = token_data.get("refresh_token", config.refresh_token)
                expires_in = token_data.get("expires_in", 3600)
                config.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                self.session.add(config)
                self.session.commit()
                # Update connector config reference
                connector.config = config

            total_records = 0
            completed_entities = []

            # Get delta sync start time if needed
            since = None
            if not full_sync and config.last_sync_at:
                since = config.last_sync_at

            # Sync each entity type
            for entity_key in entities:
                try:
                    logger.info(f"[CarbonVoice] Syncing entity: {entity_key}")
                    records = await self._sync_entity(
                        connector=connector,
                        config=config,
                        sync_log=sync_log,
                        entity_key=entity_key,
                        since=since,
                    )
                    total_records += records
                    completed_entities.append(entity_key)

                    # Update sync log progress
                    sync_log.entities_completed = completed_entities
                    sync_log.total_records_fetched = total_records
                    self.session.add(sync_log)
                    self.session.commit()

                except Exception as e:
                    logger.error(f"[CarbonVoice] Error syncing {entity_key}: {e}")
                    # Continue with other entities

            # Mark sync as completed
            sync_log.sync_status = SyncStatus.COMPLETED
            sync_log.completed_at = datetime.utcnow()
            sync_log.total_records_fetched = total_records
            self.session.add(sync_log)

            # Update config
            config.last_sync_at = datetime.utcnow()
            config.last_sync_status = SyncStatus.COMPLETED
            config.last_sync_error = None
            self.session.add(config)
            self.session.commit()

            logger.info(
                f"[CarbonVoice] Sync completed for config {connector_config_id}. "
                f"Total records: {total_records}"
            )

            return sync_log

        except Exception as e:
            logger.error(f"[CarbonVoice] Sync failed for config {connector_config_id}: {e}")

            # Update sync log
            sync_log.sync_status = SyncStatus.FAILED
            sync_log.completed_at = datetime.utcnow()
            sync_log.error_message = str(e)
            self.session.add(sync_log)

            # Update config
            config.last_sync_status = SyncStatus.FAILED
            config.last_sync_error = str(e)
            self.session.add(config)
            self.session.commit()

            raise

    async def _sync_entity(
        self,
        connector: CarbonVoiceConnector,
        config: ConnectorConfig,
        sync_log: ConnectorSyncLog,
        entity_key: str,
        since: Optional[datetime] = None,
    ) -> int:
        """
        Sync a specific entity type.

        Args:
            connector: CarbonVoiceConnector instance
            config: ConnectorConfig
            sync_log: Current sync log
            entity_key: Entity type to sync
            since: For delta syncs, fetch data since this time

        Returns:
            Number of records synced
        """
        records_synced = 0

        if entity_key == "workspace":
            records_synced = await self._sync_workspaces(connector, config, sync_log)
        elif entity_key == "channel":
            records_synced = await self._sync_channels(connector, config, sync_log)
        elif entity_key == "message":
            records_synced = await self._sync_messages(connector, config, sync_log)
        elif entity_key == "action_item":
            records_synced = await self._sync_action_items(connector, config, sync_log)
        else:
            logger.warning(f"[CarbonVoice] Unknown entity type: {entity_key}")

        return records_synced

    async def _sync_workspaces(
        self,
        connector: CarbonVoiceConnector,
        config: ConnectorConfig,
        sync_log: ConnectorSyncLog,
    ) -> int:
        """Sync workspaces"""
        workspaces = await connector.get_workspaces()
        records_synced = 0

        for workspace in workspaces:
            workspace_id = connector.get_entity_external_id("workspace", workspace)
            if not workspace_id:
                continue

            # Check if record exists
            existing = self.session.exec(
                select(ConnectorRawData).where(
                    ConnectorRawData.connector_config_id == config.id,
                    ConnectorRawData.entity_type == "workspace",
                    ConnectorRawData.external_id == workspace_id,
                )
            ).first()

            if existing:
                # Update existing record
                existing.raw_data = workspace
                existing.updated_at = datetime.utcnow()
                existing.sync_log_id = sync_log.id
                existing.is_processed = False  # Mark for reprocessing
                self.session.add(existing)
            else:
                # Create new record
                raw_data = ConnectorRawData(
                    connector_config_id=config.id,
                    tenant_id=config.tenant_id,
                    company_id=config.company_id,
                    connector_type=ConnectorType.CARBONVOICE,
                    entity_type="workspace",
                    external_id=workspace_id,
                    raw_data=workspace,
                    sync_log_id=sync_log.id,
                    external_updated_at=connector.get_entity_updated_at("workspace", workspace),
                )
                self.session.add(raw_data)

            records_synced += 1

        self.session.commit()
        logger.info(f"[CarbonVoice] Synced {records_synced} workspaces")
        return records_synced

    async def _sync_channels(
        self,
        connector: CarbonVoiceConnector,
        config: ConnectorConfig,
        sync_log: ConnectorSyncLog,
    ) -> int:
        """Sync channels for all workspaces"""
        # First get all workspaces
        workspaces = await connector.get_workspaces()
        records_synced = 0

        for workspace in workspaces:
            workspace_id = connector.get_entity_external_id("workspace", workspace)
            if not workspace_id:
                continue

            try:
                channels = await connector.get_channels(workspace_id)

                for channel in channels:
                    channel_id = connector.get_entity_external_id("channel", channel)
                    if not channel_id:
                        continue

                    # Add workspace reference to channel data
                    channel["_workspace_guid"] = workspace_id

                    # Check if record exists
                    existing = self.session.exec(
                        select(ConnectorRawData).where(
                            ConnectorRawData.connector_config_id == config.id,
                            ConnectorRawData.entity_type == "channel",
                            ConnectorRawData.external_id == channel_id,
                        )
                    ).first()

                    if existing:
                        existing.raw_data = channel
                        existing.updated_at = datetime.utcnow()
                        existing.sync_log_id = sync_log.id
                        existing.is_processed = False
                        self.session.add(existing)
                    else:
                        raw_data = ConnectorRawData(
                            connector_config_id=config.id,
                            tenant_id=config.tenant_id,
                            company_id=config.company_id,
                            connector_type=ConnectorType.CARBONVOICE,
                            entity_type="channel",
                            external_id=channel_id,
                            raw_data=channel,
                            sync_log_id=sync_log.id,
                            external_updated_at=connector.get_entity_updated_at("channel", channel),
                        )
                        self.session.add(raw_data)

                    records_synced += 1

            except Exception as e:
                logger.warning(f"[CarbonVoice] Error syncing channels for workspace {workspace_id}: {e}")

        self.session.commit()
        logger.info(f"[CarbonVoice] Synced {records_synced} channels")
        return records_synced

    async def _sync_messages(
        self,
        connector: CarbonVoiceConnector,
        config: ConnectorConfig,
        sync_log: ConnectorSyncLog,
        batch_size: int = 100,
    ) -> int:
        """Sync messages for all channels"""
        # Get all channel raw data records
        channels = self.session.exec(
            select(ConnectorRawData).where(
                ConnectorRawData.connector_config_id == config.id,
                ConnectorRawData.entity_type == "channel",
            )
        ).all()

        records_synced = 0

        for channel_record in channels:
            channel_id = channel_record.external_id
            if not channel_id:
                continue

            try:
                # Fetch messages in batches using sequence numbers
                start = 0
                while True:
                    messages = await connector.get_messages(
                        channel_id=channel_id,
                        start=start,
                        stop=start + batch_size,
                    )

                    if not messages:
                        break

                    for message in messages:
                        message_id = connector.get_entity_external_id("message", message)
                        if not message_id:
                            continue

                        # Add channel reference
                        message["_channel_id"] = channel_id

                        # Check if record exists
                        existing = self.session.exec(
                            select(ConnectorRawData).where(
                                ConnectorRawData.connector_config_id == config.id,
                                ConnectorRawData.entity_type == "message",
                                ConnectorRawData.external_id == message_id,
                            )
                        ).first()

                        if existing:
                            existing.raw_data = message
                            existing.updated_at = datetime.utcnow()
                            existing.sync_log_id = sync_log.id
                            existing.is_processed = False
                            self.session.add(existing)
                        else:
                            raw_data = ConnectorRawData(
                                connector_config_id=config.id,
                                tenant_id=config.tenant_id,
                                company_id=config.company_id,
                                connector_type=ConnectorType.CARBONVOICE,
                                entity_type="message",
                                external_id=message_id,
                                raw_data=message,
                                sync_log_id=sync_log.id,
                                external_updated_at=connector.get_entity_updated_at("message", message),
                            )
                            self.session.add(raw_data)

                        records_synced += 1

                    # Commit in batches
                    if records_synced % 500 == 0:
                        self.session.commit()

                    # Check if we got fewer messages than requested (end of data)
                    if len(messages) < batch_size:
                        break

                    start += batch_size

            except Exception as e:
                logger.warning(f"[CarbonVoice] Error syncing messages for channel {channel_id}: {e}")

        self.session.commit()
        logger.info(f"[CarbonVoice] Synced {records_synced} messages")
        return records_synced

    async def _sync_action_items(
        self,
        connector: CarbonVoiceConnector,
        config: ConnectorConfig,
        sync_log: ConnectorSyncLog,
    ) -> int:
        """Sync action items for all workspaces"""
        workspaces = await connector.get_workspaces()
        records_synced = 0

        for workspace in workspaces:
            workspace_id = connector.get_entity_external_id("workspace", workspace)
            if not workspace_id:
                continue

            try:
                action_items = await connector.get_action_items("workspace", workspace_id)

                for action_item in action_items:
                    item_id = connector.get_entity_external_id("action_item", action_item)
                    if not item_id:
                        continue

                    # Add workspace reference
                    action_item["_workspace_guid"] = workspace_id

                    existing = self.session.exec(
                        select(ConnectorRawData).where(
                            ConnectorRawData.connector_config_id == config.id,
                            ConnectorRawData.entity_type == "action_item",
                            ConnectorRawData.external_id == item_id,
                        )
                    ).first()

                    if existing:
                        existing.raw_data = action_item
                        existing.updated_at = datetime.utcnow()
                        existing.sync_log_id = sync_log.id
                        existing.is_processed = False
                        self.session.add(existing)
                    else:
                        raw_data = ConnectorRawData(
                            connector_config_id=config.id,
                            tenant_id=config.tenant_id,
                            company_id=config.company_id,
                            connector_type=ConnectorType.CARBONVOICE,
                            entity_type="action_item",
                            external_id=item_id,
                            raw_data=action_item,
                            sync_log_id=sync_log.id,
                            external_updated_at=connector.get_entity_updated_at("action_item", action_item),
                        )
                        self.session.add(raw_data)

                    records_synced += 1

            except Exception as e:
                logger.warning(f"[CarbonVoice] Error syncing action items for workspace {workspace_id}: {e}")

        self.session.commit()
        logger.info(f"[CarbonVoice] Synced {records_synced} action items")
        return records_synced
