"""
WebSocket manager for connector ingestion progress updates.
"""
import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket
from utils.logger import get_logger
from config.settings import AZURE_REDIS_CONNECTION_STRING

logger = get_logger(__name__)

# Redis channel for connector WebSocket messages
REDIS_CHANNEL = "websocket:connector_progress"


def _get_tenant_from_db(connector_config_id: str) -> Optional[str]:
    """
    Lookup tenant_id from database for a connector config.
    Used when in-memory cache doesn't have the mapping (multi-worker scenario).
    """
    try:
        from database.connection import engine
        from sqlmodel import Session
        from database.models.connector import ConnectorConfig

        with Session(engine) as session:
            config = session.get(ConnectorConfig, connector_config_id)
            if config:
                return config.tenant_id
    except Exception as e:
        logger.error(f"[ConnectorWebSocket] Failed to lookup tenant from DB: {e}")
    return None


class ConnectorWebSocketManager:
    """
    Manages WebSocket connections for connector ingestion progress updates.
    One connection per user, broadcasts progress for all their connectors.
    Uses Redis pub/sub for multi-worker support.
    """

    def __init__(self):
        # Map: tenant_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Map: connector_config_id -> tenant_id (for routing progress updates)
        self._connector_tenants: Dict[str, str] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        # Redis client (initialized lazily)
        self._redis = None
        self._pubsub = None
        self._listener_task = None

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            import redis.asyncio as aioredis
            redis_url = AZURE_REDIS_CONNECTION_STRING
            if not redis_url:
                logger.warning("[ConnectorWebSocket] AZURE_REDIS_CONNECTION_STRING not set")
                return None
            try:
                # For Azure Redis SSL connections, pass password explicitly
                if redis_url.startswith("rediss://"):
                    # Parse: rediss://:PASSWORD@HOST:PORT/DB
                    url_without_scheme = redis_url[len("rediss://:"):]
                    at_index = url_without_scheme.rfind("@")
                    if at_index != -1:
                        password = url_without_scheme[:at_index]
                        host_part = url_without_scheme[at_index + 1:]
                        if "/" in host_part:
                            host_port, db_str = host_part.rsplit("/", 1)
                            db = int(db_str) if db_str else 0
                        else:
                            host_port = host_part
                            db = 0
                        host, port_str = host_port.rsplit(":", 1)
                        port = int(port_str)
                        logger.info(f"[ConnectorWebSocket] Connecting to Redis at {host}:{port} db={db}")
                        self._redis = aioredis.Redis(
                            host=host,
                            port=port,
                            db=db,
                            username="default",
                            password=password,
                            ssl=True,
                            decode_responses=True
                        )
                    else:
                        logger.error("[ConnectorWebSocket] Invalid Redis URL format")
                        return None
                else:
                    self._redis = aioredis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info("[ConnectorWebSocket] Connected to Redis")
            except Exception as e:
                logger.error(f"[ConnectorWebSocket] Failed to connect to Redis: {e}")
                self._redis = None
        return self._redis

    async def start_listener(self):
        """Start the Redis pub/sub listener."""
        redis_client = await self._get_redis()
        if not redis_client:
            logger.warning("[ConnectorWebSocket] Redis not available, running in single-worker mode")
            return

        try:
            self._pubsub = redis_client.pubsub()
            await self._pubsub.subscribe(REDIS_CHANNEL)
            self._listener_task = asyncio.create_task(self._listen_to_redis())
            logger.info("[ConnectorWebSocket] Redis listener started")
        except Exception as e:
            logger.error(f"[ConnectorWebSocket] Failed to start Redis listener: {e}")

    async def _listen_to_redis(self):
        """Listen for messages from Redis and forward to local WebSocket connections."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        tenant_id = data.get("tenant_id")
                        payload = data.get("payload")
                        if tenant_id and payload:
                            await self._send_to_tenant(tenant_id, payload)
                    except json.JSONDecodeError:
                        logger.warning("[ConnectorWebSocket] Invalid JSON from Redis")
                    except Exception as e:
                        logger.error(f"[ConnectorWebSocket] Error processing Redis message: {e}")
        except asyncio.CancelledError:
            logger.info("[ConnectorWebSocket] Redis listener stopped")
        except Exception as e:
            logger.error(f"[ConnectorWebSocket] Redis listener error: {e}")

    async def stop_listener(self):
        """Stop the Redis pub/sub listener."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe(REDIS_CHANNEL)
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("[ConnectorWebSocket] Redis listener stopped")

    async def connect(self, websocket: WebSocket, tenant_id: str):
        """Accept a new WebSocket connection for a tenant."""
        await websocket.accept()
        async with self._lock:
            if tenant_id not in self._connections:
                self._connections[tenant_id] = set()
            self._connections[tenant_id].add(websocket)
        logger.info(f"[ConnectorWebSocket] Client connected for tenant: {tenant_id}")

    async def disconnect(self, websocket: WebSocket, tenant_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if tenant_id in self._connections:
                self._connections[tenant_id].discard(websocket)
                if not self._connections[tenant_id]:
                    del self._connections[tenant_id]
        logger.info(f"[ConnectorWebSocket] Client disconnected for tenant: {tenant_id}")

    def register_connector(self, connector_config_id: str, tenant_id: str):
        """Register a connector for progress tracking."""
        self._connector_tenants[connector_config_id] = tenant_id
        logger.info(f"[ConnectorWebSocket] Registered connector {connector_config_id} for tenant {tenant_id}")

    def unregister_connector(self, connector_config_id: str):
        """Unregister a connector from progress tracking."""
        if connector_config_id in self._connector_tenants:
            del self._connector_tenants[connector_config_id]

    async def broadcast_progress(
        self,
        connector_config_id: str,
        step: int,
        step_name: str,
        progress: int,
        status: str = "processing",
        current_entity: str = None,
        entities_completed: list = None,
        records_processed: int = None,
        chunks_created: int = None,
        error_message: str = None
    ):
        """
        Broadcast progress update to all connected clients for the connector's tenant.
        Publishes to Redis so all workers can receive and forward to their connections.
        """
        tenant_id = self._connector_tenants.get(connector_config_id)

        # Fallback to DB lookup if not in memory (multi-worker scenario)
        if not tenant_id:
            tenant_id = _get_tenant_from_db(connector_config_id)
            if tenant_id:
                self._connector_tenants[connector_config_id] = tenant_id
                logger.info(f"[ConnectorWebSocket] Resolved tenant {tenant_id} from DB for connector {connector_config_id}")

        if not tenant_id:
            logger.warning(f"[ConnectorWebSocket] No tenant found for connector: {connector_config_id}")
            return

        message = {
            "type": "ingestion_progress",
            "connector_config_id": connector_config_id,
            "step": step,
            "step_name": step_name,
            "progress": progress,
            "status": status,
        }
        if current_entity:
            message["current_entity"] = current_entity
        if entities_completed:
            message["entities_completed"] = entities_completed
        if records_processed is not None:
            message["records_processed"] = records_processed
        if chunks_created is not None:
            message["chunks_created"] = chunks_created
        if error_message:
            message["error_message"] = error_message

        # Publish to Redis for all workers to receive
        await self._publish_to_redis(tenant_id, message)

    async def _publish_to_redis(self, tenant_id: str, payload: dict):
        """Publish a message to Redis channel."""
        redis_client = await self._get_redis()
        if redis_client:
            try:
                message = json.dumps({"tenant_id": tenant_id, "payload": payload})
                await redis_client.publish(REDIS_CHANNEL, message)
                logger.debug(f"[ConnectorWebSocket] Published to Redis for tenant {tenant_id}")
            except Exception as e:
                logger.error(f"[ConnectorWebSocket] Failed to publish to Redis: {e}")
                # Fallback to local send if Redis fails
                await self._send_to_tenant(tenant_id, payload)
        else:
            # No Redis, send directly (single-worker mode)
            await self._send_to_tenant(tenant_id, payload)

    async def _send_to_tenant(self, tenant_id: str, message: dict):
        """Send a message to all connections for a tenant."""
        if tenant_id not in self._connections:
            return

        dead_connections = set()
        for websocket in self._connections[tenant_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"[ConnectorWebSocket] Failed to send message: {e}")
                dead_connections.add(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            await self.disconnect(ws, tenant_id)

    async def send_ping(self, tenant_id: str):
        """Send a ping to keep the connection alive."""
        await self._send_to_tenant(tenant_id, {"type": "ping"})

    def get_connection_count(self, tenant_id: str = None) -> int:
        """Get the number of active connections."""
        if tenant_id:
            return len(self._connections.get(tenant_id, set()))
        return sum(len(conns) for conns in self._connections.values())


# Global instance
connector_ws_manager = ConnectorWebSocketManager()
