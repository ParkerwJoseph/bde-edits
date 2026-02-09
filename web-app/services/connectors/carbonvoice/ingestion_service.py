"""
Carbon Voice Ingestion Service.
Processes raw Carbon Voice data into chunks for RAG.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select

from database.models.connector import (
    ConnectorConfig,
    ConnectorRawData,
    ConnectorChunk,
    ConnectorType,
)
from utils.logger import get_logger

logger = get_logger(__name__)


# Pillar mapping for Carbon Voice entities
ENTITY_PILLAR_MAP = {
    "workspace": "operational_maturity",
    "channel": "customer_health",
    "message": "customer_health",
    "action_item": "operational_maturity",
}


class CarbonVoiceIngestionService:
    """
    Service for processing Carbon Voice raw data into chunks.
    """

    def __init__(self, session: Session):
        self.session = session

    async def process_raw_data(
        self,
        connector_config_id: str,
        entity_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process raw Carbon Voice data into chunks.

        Args:
            connector_config_id: ID of the connector config
            entity_types: Optional list of entity types to process

        Returns:
            Dict with processing stats
        """
        config = self.session.get(ConnectorConfig, connector_config_id)
        if not config:
            raise ValueError(f"Connector config not found: {connector_config_id}")

        # Get unprocessed raw data
        query = select(ConnectorRawData).where(
            ConnectorRawData.connector_config_id == connector_config_id,
            ConnectorRawData.is_processed == False,
        )

        if entity_types:
            query = query.where(ConnectorRawData.entity_type.in_(entity_types))

        raw_records = self.session.exec(query).all()

        stats = {
            "total_records": len(raw_records),
            "chunks_created": 0,
            "entities_processed": {},
            "errors": [],
        }

        for raw_record in raw_records:
            try:
                chunks = await self._process_record(raw_record, config)
                stats["chunks_created"] += len(chunks)

                # Track by entity type
                entity_type = raw_record.entity_type
                if entity_type not in stats["entities_processed"]:
                    stats["entities_processed"][entity_type] = 0
                stats["entities_processed"][entity_type] += 1

                # Mark as processed
                raw_record.is_processed = True
                raw_record.processed_at = datetime.utcnow()
                self.session.add(raw_record)

            except Exception as e:
                logger.error(f"[CarbonVoice] Error processing record {raw_record.id}: {e}")
                stats["errors"].append({
                    "record_id": raw_record.id,
                    "error": str(e),
                })

        self.session.commit()

        logger.info(
            f"[CarbonVoice] Ingestion completed. "
            f"Records: {stats['total_records']}, Chunks: {stats['chunks_created']}"
        )

        return stats

    async def _process_record(
        self,
        raw_record: ConnectorRawData,
        config: ConnectorConfig,
    ) -> List[ConnectorChunk]:
        """
        Process a single raw data record into chunks.

        Args:
            raw_record: Raw data record
            config: Connector config

        Returns:
            List of created chunks
        """
        entity_type = raw_record.entity_type
        raw_data = raw_record.raw_data

        if entity_type == "workspace":
            return await self._process_workspace(raw_record, config)
        elif entity_type == "channel":
            return await self._process_channel(raw_record, config)
        elif entity_type == "message":
            return await self._process_message(raw_record, config)
        elif entity_type == "action_item":
            return await self._process_action_item(raw_record, config)
        else:
            logger.warning(f"[CarbonVoice] Unknown entity type: {entity_type}")
            return []

    async def _process_workspace(
        self,
        raw_record: ConnectorRawData,
        config: ConnectorConfig,
    ) -> List[ConnectorChunk]:
        """Process workspace into chunk"""
        data = raw_record.raw_data
        chunks = []

        workspace_name = data.get("workspace_name", "Unknown Workspace")
        workspace_desc = data.get("workspace_description", "")
        owner_name = f"{data.get('creator_first_name', '')} {data.get('creator_last_name', '')}".strip()
        member_count = len(data.get("collaborators", []))
        channel_count = len(data.get("channels", []))

        # Create summary content
        content = f"""Workspace: {workspace_name}

Description: {workspace_desc or 'No description provided'}

Owner: {owner_name or 'Unknown'}
Members: {member_count}
Channels: {channel_count}
Plan Type: {data.get('plan_type', 'Unknown')}

This workspace is part of the Carbon Voice communication platform and contains
{channel_count} conversation channels with {member_count} team members."""

        summary = f"Carbon Voice workspace '{workspace_name}' with {member_count} members and {channel_count} channels"

        chunk = ConnectorChunk(
            tenant_id=config.tenant_id,
            company_id=config.company_id,
            connector_config_id=config.id,
            connector_type=ConnectorType.CARBONVOICE,
            raw_data_id=raw_record.id,
            entity_type="workspace",
            entity_id=raw_record.external_id,
            entity_name=workspace_name,
            content=content,
            summary=summary,
            pillar=ENTITY_PILLAR_MAP.get("workspace", "operational_maturity"),
            chunk_type="connector_data",
            metadata_json={
                "workspace_name": workspace_name,
                "member_count": member_count,
                "channel_count": channel_count,
                "plan_type": data.get("plan_type"),
            },
            data_as_of=datetime.utcnow(),
        )

        self.session.add(chunk)
        chunks.append(chunk)

        return chunks

    async def _process_channel(
        self,
        raw_record: ConnectorRawData,
        config: ConnectorConfig,
    ) -> List[ConnectorChunk]:
        """Process channel into chunk"""
        data = raw_record.raw_data
        chunks = []

        channel_name = data.get("channel_name", "Unknown Channel")
        channel_desc = data.get("channel_description", "")
        channel_kind = data.get("channel_kind", "standard")
        workspace_name = data.get("workspace_name", "")
        is_private = data.get("is_private", "N") == "Y"
        collaborators = data.get("json_collaborators", [])
        total_messages = data.get("total_messages", 0)

        # Create content
        visibility = "private" if is_private else "public"
        content = f"""Conversation Channel: {channel_name}

Workspace: {workspace_name or 'Unknown'}
Type: {channel_kind}
Visibility: {visibility}
Description: {channel_desc or 'No description'}

Participants: {len(collaborators)}
Total Messages: {total_messages}

This is a {visibility} {channel_kind} conversation channel in Carbon Voice
with {len(collaborators)} active participants."""

        summary = f"Carbon Voice channel '{channel_name}' ({visibility}) with {len(collaborators)} participants and {total_messages} messages"

        chunk = ConnectorChunk(
            tenant_id=config.tenant_id,
            company_id=config.company_id,
            connector_config_id=config.id,
            connector_type=ConnectorType.CARBONVOICE,
            raw_data_id=raw_record.id,
            entity_type="channel",
            entity_id=raw_record.external_id,
            entity_name=channel_name,
            content=content,
            summary=summary,
            pillar=ENTITY_PILLAR_MAP.get("channel", "customer_health"),
            chunk_type="connector_data",
            metadata_json={
                "channel_name": channel_name,
                "channel_kind": channel_kind,
                "is_private": is_private,
                "participant_count": len(collaborators),
                "total_messages": total_messages,
                "workspace_guid": data.get("_workspace_guid"),
            },
            data_as_of=datetime.utcnow(),
        )

        self.session.add(chunk)
        chunks.append(chunk)

        return chunks

    async def _process_message(
        self,
        raw_record: ConnectorRawData,
        config: ConnectorConfig,
    ) -> List[ConnectorChunk]:
        """Process message into chunk"""
        data = raw_record.raw_data
        chunks = []

        # Extract message content
        transcript = data.get("transcript", "")
        summary_text = data.get("summary", "")
        topic = data.get("topic", "")

        # If no transcript, try to get from text models
        if not transcript:
            text_models = data.get("text_models", [])
            for tm in text_models:
                if tm.get("type") == "transcript":
                    transcript = tm.get("text", "")
                    break

        # Skip messages without meaningful content
        if not transcript and not summary_text:
            raw_record.is_processed = True
            raw_record.processed_at = datetime.utcnow()
            return []

        # Get sender info
        creator_id = data.get("creator_id", "")
        channel_id = data.get("_channel_id", data.get("channel_id", ""))

        # Get timestamp
        created_ts = data.get("created_ts")
        created_at = None
        if created_ts:
            if isinstance(created_ts, (int, float)):
                if created_ts > 1e12:
                    created_at = datetime.utcfromtimestamp(created_ts / 1000)
                else:
                    created_at = datetime.utcfromtimestamp(created_ts)

        # Create content
        content_parts = []
        if topic:
            content_parts.append(f"Topic: {topic}")
        if transcript:
            content_parts.append(f"Message Content:\n{transcript}")
        if summary_text:
            content_parts.append(f"Summary: {summary_text}")

        content = "\n\n".join(content_parts)

        # Create summary
        if summary_text:
            summary = summary_text[:200]
        elif transcript:
            summary = f"Voice message: {transcript[:200]}..."
        else:
            summary = "Carbon Voice message"

        chunk = ConnectorChunk(
            tenant_id=config.tenant_id,
            company_id=config.company_id,
            connector_config_id=config.id,
            connector_type=ConnectorType.CARBONVOICE,
            raw_data_id=raw_record.id,
            entity_type="message",
            entity_id=raw_record.external_id,
            entity_name=topic or f"Message from {creator_id[:8]}..." if creator_id else "Voice Message",
            content=content,
            summary=summary,
            pillar=ENTITY_PILLAR_MAP.get("message", "customer_health"),
            chunk_type="connector_data",
            metadata_json={
                "channel_id": channel_id,
                "creator_id": creator_id,
                "has_audio": bool(data.get("audio_info")),
                "has_attachments": bool(data.get("attachments")),
                "reaction_count": len(data.get("reactions", [])),
            },
            data_as_of=created_at,
        )

        self.session.add(chunk)
        chunks.append(chunk)

        return chunks

    async def _process_action_item(
        self,
        raw_record: ConnectorRawData,
        config: ConnectorConfig,
    ) -> List[ConnectorChunk]:
        """Process action item into chunk"""
        data = raw_record.raw_data
        chunks = []

        title = data.get("title", data.get("text", "Untitled Action Item"))
        status = data.get("status", "pending")
        assignee_id = data.get("assignee_id", "")
        workspace_guid = data.get("_workspace_guid", "")

        # Get due date if available
        due_date = data.get("due_date")
        due_str = ""
        if due_date:
            if isinstance(due_date, str):
                due_str = due_date
            elif isinstance(due_date, (int, float)):
                due_str = datetime.utcfromtimestamp(due_date / 1000 if due_date > 1e12 else due_date).isoformat()

        content = f"""Action Item: {title}

Status: {status}
Assignee: {assignee_id or 'Unassigned'}
Due Date: {due_str or 'Not set'}

This action item was created from a Carbon Voice conversation
and is currently {status}."""

        summary = f"Action item '{title}' - Status: {status}"

        chunk = ConnectorChunk(
            tenant_id=config.tenant_id,
            company_id=config.company_id,
            connector_config_id=config.id,
            connector_type=ConnectorType.CARBONVOICE,
            raw_data_id=raw_record.id,
            entity_type="action_item",
            entity_id=raw_record.external_id,
            entity_name=title,
            content=content,
            summary=summary,
            pillar=ENTITY_PILLAR_MAP.get("action_item", "operational_maturity"),
            chunk_type="connector_data",
            metadata_json={
                "status": status,
                "assignee_id": assignee_id,
                "workspace_guid": workspace_guid,
                "due_date": due_str,
            },
            data_as_of=datetime.utcnow(),
        )

        self.session.add(chunk)
        chunks.append(chunk)

        return chunks

    async def generate_aggregated_summaries(
        self,
        connector_config_id: str,
    ) -> Dict[str, Any]:
        """
        Generate aggregated summary chunks from individual chunks.
        This creates higher-level insights from the raw data.

        Args:
            connector_config_id: ID of the connector config

        Returns:
            Dict with summary stats
        """
        config = self.session.get(ConnectorConfig, connector_config_id)
        if not config:
            raise ValueError(f"Connector config not found: {connector_config_id}")

        # Get all chunks for this connector
        chunks = self.session.exec(
            select(ConnectorChunk).where(
                ConnectorChunk.connector_config_id == connector_config_id,
                ConnectorChunk.chunk_type == "connector_data",
            )
        ).all()

        # Group by entity type
        by_type = {}
        for chunk in chunks:
            if chunk.entity_type not in by_type:
                by_type[chunk.entity_type] = []
            by_type[chunk.entity_type].append(chunk)

        stats = {
            "summaries_created": 0,
            "by_entity_type": {},
        }

        # Create summary for each entity type
        for entity_type, entity_chunks in by_type.items():
            summary_content = f"""Carbon Voice {entity_type.title()} Summary

Total {entity_type}s: {len(entity_chunks)}

This summary covers all {entity_type} data synced from Carbon Voice
for this company's communication and collaboration activities."""

            summary_chunk = ConnectorChunk(
                tenant_id=config.tenant_id,
                company_id=config.company_id,
                connector_config_id=config.id,
                connector_type=ConnectorType.CARBONVOICE,
                entity_type=entity_type,
                entity_name=f"{entity_type.title()} Summary",
                content=summary_content,
                summary=f"Aggregated summary of {len(entity_chunks)} {entity_type}s from Carbon Voice",
                pillar=ENTITY_PILLAR_MAP.get(entity_type, "operational_maturity"),
                chunk_type="aggregated_summary",
                metadata_json={
                    "count": len(entity_chunks),
                    "entity_type": entity_type,
                },
                data_as_of=datetime.utcnow(),
            )

            self.session.add(summary_chunk)
            stats["summaries_created"] += 1
            stats["by_entity_type"][entity_type] = len(entity_chunks)

        self.session.commit()

        logger.info(f"[CarbonVoice] Created {stats['summaries_created']} aggregated summaries")
        return stats
