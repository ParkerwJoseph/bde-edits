"""API routes for Carbon Voice connector management"""

import secrets
from typing import Optional, List
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from sqlalchemy import func

from config.settings import FRONTEND_URL, WEBHOOK_SECRET

from database.connection import get_session
from database.models import User, Company
from database.models.connector import (
    ConnectorConfig,
    ConnectorSyncLog,
    ConnectorRawData,
    ConnectorChunk,
    ConnectorType,
    ConnectorStatus,
    SyncStatus,
)
from az_auth.dependencies import get_current_user, require_permission
from core.permissions import Permissions
from services.connectors.carbonvoice.client import CarbonVoiceConnector
from services.connectors.carbonvoice.sync_service import CarbonVoiceSyncService
from services.connectors.carbonvoice.ingestion_service import CarbonVoiceIngestionService
from services.storage import send_carbonvoice_processing_message
from api.connector.schemas import (
    ConnectorConfigResponse,
    ConnectorConfigListResponse,
    ConnectorConfigUpdate,
    OAuthStartResponse,
    DiscoverEntitiesResponse,
    EntityInfo,
    SyncRequest,
    SyncStartResponse,
    SyncStatusResponse,
    SyncLogResponse,
    SyncLogListResponse,
    IngestionRequest,
    IngestionResponse,
    IngestionWebhookPayload,
    SupportedConnectorInfo,
)
from api.connector.websocket_manager import connector_ws_manager
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _get_enum_value(enum_val) -> str:
    """Get the string value from an enum or string, handling case variations."""
    if hasattr(enum_val, 'value'):
        return enum_val.value.lower()
    return str(enum_val).lower()


def _is_carbonvoice_connector(config: ConnectorConfig) -> bool:
    """Check if config is a Carbon Voice connector."""
    return _get_enum_value(config.connector_type) == ConnectorType.CARBONVOICE.value


def _is_connected(config: ConnectorConfig) -> bool:
    """Check if connector is in connected state."""
    return _get_enum_value(config.connector_status) == ConnectorStatus.CONNECTED.value


# ============================================================================
# Carbon Voice Info
# ============================================================================

@router.get("/info", response_model=SupportedConnectorInfo)
async def get_carbonvoice_info(
    user: User = Depends(require_permission(Permissions.FILES_READ)),
):
    """Get Carbon Voice connector info and configuration status"""
    connector = CarbonVoiceConnector()

    return SupportedConnectorInfo(
        connector_type="carbonvoice",
        display_name="Carbon Voice",
        description="Connect to Carbon Voice for voice messaging and collaboration data",
        is_configured=connector.is_configured(),
    )


# ============================================================================
# Connector Config CRUD
# ============================================================================

@router.get("/", response_model=ConnectorConfigListResponse)
async def list_carbonvoice_connectors(
    company_id: Optional[str] = None,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """List all Carbon Voice connector configs for tenant"""
    query = select(ConnectorConfig).where(
        ConnectorConfig.tenant_id == user.tenant_id,
        func.lower(ConnectorConfig.connector_type) == ConnectorType.CARBONVOICE.value
    )

    if company_id:
        query = query.where(ConnectorConfig.company_id == company_id)

    query = query.order_by(ConnectorConfig.created_at.desc())

    configs = session.exec(query).all()

    return ConnectorConfigListResponse(
        connectors=[ConnectorConfigResponse.model_validate(c) for c in configs],
        total=len(configs)
    )


@router.get("/{connector_id}", response_model=ConnectorConfigResponse)
async def get_carbonvoice_connector(
    connector_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Get Carbon Voice connector config by ID"""
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not _is_carbonvoice_connector(config):
        raise HTTPException(status_code=400, detail="Not a Carbon Voice connector")

    return ConnectorConfigResponse.model_validate(config)


@router.patch("/{connector_id}", response_model=ConnectorConfigResponse)
async def update_carbonvoice_connector(
    connector_id: str,
    update_data: ConnectorConfigUpdate,
    user: User = Depends(require_permission(Permissions.FILES_UPLOAD)),
    session: Session = Depends(get_session),
):
    """Update Carbon Voice connector config (enabled entities, sync settings)"""
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not _is_carbonvoice_connector(config):
        raise HTTPException(status_code=400, detail="Not a Carbon Voice connector")

    # Update fields
    if update_data.enabled_entities is not None:
        config.enabled_entities = update_data.enabled_entities

    if update_data.sync_settings is not None:
        config.sync_settings = update_data.sync_settings

    config.updated_at = datetime.utcnow()

    session.add(config)
    session.commit()
    session.refresh(config)

    logger.info(f"[CarbonVoice] Updated config {connector_id}")

    return ConnectorConfigResponse.model_validate(config)


@router.delete("/{connector_id}")
async def disconnect_carbonvoice(
    connector_id: str,
    user: User = Depends(require_permission(Permissions.FILES_DELETE)),
    session: Session = Depends(get_session),
):
    """Disconnect and delete a Carbon Voice connector"""
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not _is_carbonvoice_connector(config):
        raise HTTPException(status_code=400, detail="Not a Carbon Voice connector")

    # Delete related data in correct order to respect foreign key constraints
    # 1. Delete chunks first (they reference raw_data)
    chunks = session.exec(
        select(ConnectorChunk).where(ConnectorChunk.connector_config_id == connector_id)
    ).all()
    for chunk in chunks:
        session.delete(chunk)
    if chunks:
        session.commit()

    # 2. Delete raw data next (they reference sync_logs via sync_log_id)
    raw_data = session.exec(
        select(ConnectorRawData).where(ConnectorRawData.connector_config_id == connector_id)
    ).all()
    for data in raw_data:
        session.delete(data)
    if raw_data:
        session.commit()

    # 3. Delete sync logs (they reference connector_config)
    sync_logs = session.exec(
        select(ConnectorSyncLog).where(ConnectorSyncLog.connector_config_id == connector_id)
    ).all()
    for log in sync_logs:
        session.delete(log)
    if sync_logs:
        session.commit()

    # 4. Delete config last
    session.delete(config)
    session.commit()

    logger.info(f"[CarbonVoice] Deleted connector {connector_id}")

    return {"message": "Carbon Voice connector disconnected successfully"}


# ============================================================================
# OAuth
# ============================================================================

# In-memory state storage (maps state -> context)
# In production with multiple workers, use Redis instead
_oauth_states: dict = {}


def _cleanup_expired_states():
    """Remove states older than 10 minutes"""
    now = datetime.utcnow()
    expired = [k for k, v in _oauth_states.items()
               if now - v.get("created_at", now) > timedelta(minutes=10)]
    for k in expired:
        del _oauth_states[k]


@router.post("/oauth/start", response_model=OAuthStartResponse)
async def start_carbonvoice_oauth(
    company_id: str,
    user: User = Depends(require_permission(Permissions.FILES_UPLOAD)),
    session: Session = Depends(get_session),
):
    """
    Start Carbon Voice OAuth flow.
    Returns authorization URL to redirect user to Carbon Voice login.
    """
    # Verify company belongs to tenant
    company = session.get(Company, company_id)
    if not company or company.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check if connector is configured
    connector = CarbonVoiceConnector()
    if not connector.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Carbon Voice integration not configured. Contact administrator."
        )

    # Cleanup expired states
    _cleanup_expired_states()

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store context with state (needed for callback)
    _oauth_states[state] = {
        "company_id": company_id,
        "tenant_id": user.tenant_id,
        "user_id": user.id,
        "created_at": datetime.utcnow(),
    }

    # Get authorization URL
    auth_url = connector.get_authorization_url(state)

    logger.info(f"[CarbonVoice] Started OAuth for company {company_id}")

    return OAuthStartResponse(
        authorization_url=auth_url,
        state=state
    )


@router.get("/oauth/callback")
async def carbonvoice_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    Handle Carbon Voice OAuth callback (GET redirect from Carbon Voice).
    Exchanges code for tokens and redirects to frontend.
    """
    frontend_url = f"{FRONTEND_URL}/connectors"

    # Handle OAuth error from Carbon Voice
    if error:
        error_msg = error_description or error
        logger.error(f"[CarbonVoice] OAuth error: {error_msg}")
        params = urlencode({"oauth_error": error_msg})
        return RedirectResponse(url=f"{frontend_url}?{params}")

    # Validate required params
    if not code or not state:
        logger.error("[CarbonVoice] Missing OAuth params")
        params = urlencode({"oauth_error": "Missing required parameters"})
        return RedirectResponse(url=f"{frontend_url}?{params}")

    # Validate and retrieve state context
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        logger.error("[CarbonVoice] Invalid or expired state")
        params = urlencode({"oauth_error": "Invalid or expired state. Please try again."})
        return RedirectResponse(url=f"{frontend_url}?{params}")

    company_id = state_data["company_id"]
    tenant_id = state_data["tenant_id"]
    user_id = state_data["user_id"]

    connector = CarbonVoiceConnector()

    try:
        # Exchange code for tokens
        token_data = await connector.exchange_code_for_tokens(code=code)

        # Check for existing connector config
        existing = session.exec(
            select(ConnectorConfig).where(
                ConnectorConfig.company_id == company_id,
                func.lower(ConnectorConfig.connector_type) == ConnectorType.CARBONVOICE.value
            )
        ).first()

        if existing:
            # Update existing
            config = existing
            config.access_token = token_data.get("access_token")
            config.refresh_token = token_data.get("refresh_token")
            config.token_expiry = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            config.connector_status = ConnectorStatus.CONNECTED
            config.updated_at = datetime.utcnow()
        else:
            # Create new
            config = ConnectorConfig(
                tenant_id=tenant_id,
                company_id=company_id,
                connector_type=ConnectorType.CARBONVOICE,
                connector_status=ConnectorStatus.CONNECTED,
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_expiry=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600)),
                token_type=token_data.get("token_type", "Bearer"),
                connected_by=user_id,
            )

        session.add(config)
        session.commit()
        session.refresh(config)

        # Get user info from Carbon Voice
        cv_connector = CarbonVoiceConnector(config)
        try:
            user_info = await cv_connector.get_user_info()
            # Store user info as external company info
            user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
            config.external_company_name = user_name or user_info.get("email_txt", "Carbon Voice User")
            config.external_company_id = user_info.get("user_guid") or user_info.get("uuid")
            session.add(config)
            session.commit()
        except Exception as e:
            logger.warning(f"[CarbonVoice] Failed to get user info: {e}")

        # Auto-discover available entities after OAuth
        try:
            entities_data = await cv_connector.discover_available_entities()
            config.available_entities = {
                e["entity_key"]: e for e in entities_data
            }
            session.add(config)
            session.commit()
            logger.info(f"[CarbonVoice] Auto-discovered {len(entities_data)} entities for company {company_id}")
        except Exception as e:
            logger.warning(f"[CarbonVoice] Failed to auto-discover entities: {e}")

        logger.info(f"[CarbonVoice] OAuth completed for company {company_id}")

        # Redirect to frontend with success
        params = urlencode({
            "oauth_success": "true",
            "company_id": company_id,
            "connector_type": "carbonvoice",
        })
        return RedirectResponse(url=f"{frontend_url}?{params}")

    except Exception as e:
        logger.error(f"[CarbonVoice] OAuth callback failed: {e}")
        params = urlencode({"oauth_error": str(e)})
        return RedirectResponse(url=f"{frontend_url}?{params}")


# ============================================================================
# Entity Discovery
# ============================================================================

@router.get("/{connector_id}/entities", response_model=DiscoverEntitiesResponse)
async def discover_carbonvoice_entities(
    connector_id: str,
    refresh: bool = False,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Discover available entities from Carbon Voice"""
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not _is_carbonvoice_connector(config):
        raise HTTPException(status_code=400, detail="Not a Carbon Voice connector")

    if not _is_connected(config):
        raise HTTPException(status_code=400, detail="Connector not connected")

    # Return cached entities if available and not refreshing
    if not refresh and config.available_entities:
        entities = [
            EntityInfo(**entity_data)
            for entity_data in config.available_entities.values()
        ]
        return DiscoverEntitiesResponse(entities=entities)

    # Discover from Carbon Voice
    connector = CarbonVoiceConnector(config)

    try:
        # Refresh token if needed
        if config.needs_token_refresh():
            token_data = await connector.refresh_access_token()
            config.access_token = token_data.get("access_token")
            config.refresh_token = token_data.get("refresh_token", config.refresh_token)
            config.token_expiry = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            connector.config = config

        # Discover entities
        entities_data = await connector.discover_available_entities()

        # Get user info
        user_info = await connector.get_user_info()

        # Store in config
        config.available_entities = {
            e["entity_key"]: e for e in entities_data
        }
        user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
        config.external_company_name = user_name or config.external_company_name
        config.updated_at = datetime.utcnow()

        session.add(config)
        session.commit()

        entities = [EntityInfo(**e) for e in entities_data]

        logger.info(f"[CarbonVoice] Discovered {len(entities)} entities for config {connector_id}")

        return DiscoverEntitiesResponse(
            entities=entities,
            company_info={"user_name": user_name}
        )

    except Exception as e:
        logger.error(f"[CarbonVoice] Entity discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to discover entities: {str(e)}")


# ============================================================================
# Sync Operations
# ============================================================================

@router.post("/{connector_id}/sync", response_model=SyncStartResponse)
async def start_carbonvoice_sync(
    connector_id: str,
    sync_request: SyncRequest,
    user: User = Depends(require_permission(Permissions.FILES_UPLOAD)),
    session: Session = Depends(get_session),
):
    """Start syncing data from Carbon Voice"""
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not _is_carbonvoice_connector(config):
        raise HTTPException(status_code=400, detail="Not a Carbon Voice connector")

    if not _is_connected(config):
        raise HTTPException(status_code=400, detail="Connector not connected")

    # Check if sync is already in progress
    if config.last_sync_status == SyncStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Sync already in progress")

    try:
        sync_service = CarbonVoiceSyncService(session)

        sync_log = await sync_service.sync_company(
            connector_config_id=connector_id,
            entities=sync_request.entities,
            full_sync=sync_request.full_sync,
            triggered_by=user.id,
        )

        logger.info(f"[CarbonVoice] Started sync {sync_log.id} for config {connector_id}")

        return SyncStartResponse(
            sync_log_id=sync_log.id,
            status=sync_log.sync_status,
            message="Sync started successfully"
        )

    except Exception as e:
        logger.error(f"[CarbonVoice] Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/{connector_id}/sync/{sync_log_id}", response_model=SyncStatusResponse)
async def get_carbonvoice_sync_status(
    connector_id: str,
    sync_log_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Get status of a sync operation"""
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    sync_log = session.get(ConnectorSyncLog, sync_log_id)

    if not sync_log or sync_log.connector_config_id != connector_id:
        raise HTTPException(status_code=404, detail="Sync log not found")

    return SyncStatusResponse(
        id=sync_log.id,
        status=sync_log.sync_status,
        sync_type=sync_log.sync_type,
        entities_requested=sync_log.entities_requested,
        entities_completed=sync_log.entities_completed,
        total_records_fetched=sync_log.total_records_fetched,
        total_records_processed=sync_log.total_records_processed,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
        error_message=sync_log.error_message,
    )


@router.get("/{connector_id}/sync-logs", response_model=SyncLogListResponse)
async def list_carbonvoice_sync_logs(
    connector_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """List sync logs for a Carbon Voice connector"""
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    query = select(ConnectorSyncLog).where(
        ConnectorSyncLog.connector_config_id == connector_id
    ).order_by(
        ConnectorSyncLog.started_at.desc()
    ).offset(skip).limit(limit)

    logs = session.exec(query).all()

    # Get total count
    count_query = select(ConnectorSyncLog).where(
        ConnectorSyncLog.connector_config_id == connector_id
    )
    total = len(session.exec(count_query).all())

    return SyncLogListResponse(
        sync_logs=[SyncLogResponse.model_validate(log) for log in logs],
        total=total
    )


# ============================================================================
# Ingestion Operations
# ============================================================================

@router.post("/{connector_id}/ingest", response_model=IngestionResponse)
async def process_carbonvoice_data(
    connector_id: str,
    ingestion_request: IngestionRequest,
    user: User = Depends(require_permission(Permissions.FILES_UPLOAD)),
    session: Session = Depends(get_session),
):
    """
    Queue raw Carbon Voice data for processing into chunks.

    This endpoint queues the ingestion request for processing by Azure Functions.
    Real-time progress updates are available via WebSocket at /ws endpoint.
    """
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not _is_carbonvoice_connector(config):
        raise HTTPException(status_code=400, detail="Not a Carbon Voice connector")

    try:
        # Register connector for WebSocket progress tracking
        connector_ws_manager.register_connector(connector_id, config.tenant_id)

        # Queue message for Azure Function processing
        success = send_carbonvoice_processing_message(
            connector_config_id=connector_id,
            tenant_id=config.tenant_id,
            company_id=config.company_id,
            entity_types=ingestion_request.entity_types,
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to queue ingestion request. Please try again."
            )

        logger.info(f"[CarbonVoice] Ingestion queued for connector: {connector_id}")

        return IngestionResponse(
            connector_config_id=connector_id,
            status="queued",
            message="Ingestion queued for processing. Connect to WebSocket for progress updates."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CarbonVoice] Failed to queue ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue ingestion: {str(e)}")


# ============================================================================
# Stats & Diagnostics
# ============================================================================

@router.get("/{connector_id}/stats")
async def get_carbonvoice_stats(
    connector_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Get stats for a Carbon Voice connector"""
    config = session.get(ConnectorConfig, connector_id)

    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")

    if config.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not _is_carbonvoice_connector(config):
        raise HTTPException(status_code=400, detail="Not a Carbon Voice connector")

    # Count raw data records
    raw_data_count = len(session.exec(
        select(ConnectorRawData).where(
            ConnectorRawData.connector_config_id == connector_id
        )
    ).all())

    # Count processed vs unprocessed
    unprocessed_count = len(session.exec(
        select(ConnectorRawData).where(
            ConnectorRawData.connector_config_id == connector_id,
            ConnectorRawData.is_processed == False
        )
    ).all())

    # Count chunks
    chunk_count = len(session.exec(
        select(ConnectorChunk).where(
            ConnectorChunk.connector_config_id == connector_id
        )
    ).all())

    # Count sync logs
    sync_count = len(session.exec(
        select(ConnectorSyncLog).where(
            ConnectorSyncLog.connector_config_id == connector_id
        )
    ).all())

    return {
        "connector_id": connector_id,
        "connector_type": _get_enum_value(config.connector_type),
        "connector_status": _get_enum_value(config.connector_status),
        "external_company_name": config.external_company_name,
        "raw_data_records": raw_data_count,
        "unprocessed_records": unprocessed_count,
        "processed_records": raw_data_count - unprocessed_count,
        "chunks_created": chunk_count,
        "sync_operations": sync_count,
        "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
        "last_sync_status": _get_enum_value(config.last_sync_status) if config.last_sync_status else None,
    }


# ============================================================================
# Webhook & WebSocket Endpoints
# ============================================================================

@router.post("/webhook/status")
async def handle_ingestion_webhook(
    payload: IngestionWebhookPayload,
    request: Request,
):
    """
    Webhook endpoint for Azure Function to report ingestion progress.

    This endpoint receives progress updates from Azure Functions and
    broadcasts them to connected WebSocket clients.
    """
    # Verify webhook secret if configured
    if WEBHOOK_SECRET:
        auth_header = request.headers.get("X-Webhook-Secret")
        if auth_header != WEBHOOK_SECRET:
            logger.warning("[CarbonVoice] Webhook request with invalid secret")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        # Broadcast progress to WebSocket clients
        await connector_ws_manager.broadcast_progress(
            connector_config_id=payload.connector_config_id,
            step=payload.step,
            step_name=payload.step_name,
            progress=payload.progress,
            status=payload.status,
            current_entity=payload.current_entity,
            entities_completed=payload.entities_completed,
            records_processed=payload.records_processed,
            chunks_created=payload.chunks_created,
            error_message=payload.error_message,
        )

        logger.debug(
            f"[CarbonVoice] Webhook received - connector: {payload.connector_config_id}, "
            f"step: {payload.step}, progress: {payload.progress}%"
        )

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"[CarbonVoice] Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.websocket("/ws/{tenant_id}")
async def connector_websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str,
):
    """
    WebSocket endpoint for real-time connector ingestion progress updates.

    Clients connect with their tenant_id to receive progress updates
    for all connectors belonging to that tenant.
    """
    await connector_ws_manager.connect(websocket, tenant_id)

    try:
        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for client messages (ping/pong, close, etc.)
                data = await websocket.receive_text()

                # Handle ping messages
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"[CarbonVoice] WebSocket receive error: {e}")
                break

    finally:
        await connector_ws_manager.disconnect(websocket, tenant_id)
        logger.info(f"[CarbonVoice] WebSocket disconnected for tenant: {tenant_id}")
