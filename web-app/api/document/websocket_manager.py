import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket
from utils.logger import get_logger
from config.settings import AZURE_REDIS_CONNECTION_STRING

logger = get_logger(__name__)

# Redis channel for WebSocket messages
REDIS_CHANNEL = "websocket:progress"
# Redis key prefix for progress cache (TTL: 1 hour)
REDIS_PROGRESS_PREFIX = "document:progress:"
REDIS_PROGRESS_TTL = 3600  # 1 hour


def _get_tenant_from_db(document_id: str) -> Optional[str]:
    """
    Lookup tenant_id from database for a document.
    Used when in-memory cache doesn't have the mapping (multi-worker scenario).
    """
    try:
        from database.connection import engine
        from sqlmodel import Session
        from database.models.document import Document

        with Session(engine) as session:
            doc = session.get(Document, document_id)
            if doc:
                return doc.tenant_id
    except Exception as e:
        logger.error(f"[WebSocket] Failed to lookup tenant from DB: {e}")
    return None


class DocumentWebSocketManager:
    """
    Manages WebSocket connections for document processing progress updates.
    One connection per user, broadcasts progress for all their documents.
    Uses Redis pub/sub for multi-worker support.
    """

    def __init__(self):
        # Map: tenant_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Map: document_id -> tenant_id (for routing progress updates)
        self._document_tenants: Dict[str, str] = {}
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
                logger.error("[WebSocket] AZURE_REDIS_CONNECTION_STRING not set")
                return None
            try:
                # For Azure Redis SSL connections, pass password explicitly
                if redis_url.startswith("rediss://"):
                    # Parse: rediss://:PASSWORD@HOST:PORT/DB
                    # Find the last @ to split password from host (password may contain special chars)
                    url_without_scheme = redis_url[len("rediss://:"):]  # Remove "rediss://:"
                    at_index = url_without_scheme.rfind("@")  # Find last @
                    if at_index != -1:
                        password = url_without_scheme[:at_index]
                        host_part = url_without_scheme[at_index + 1:]  # host:port/db
                        # Parse host:port/db
                        if "/" in host_part:
                            host_port, db_str = host_part.rsplit("/", 1)
                            db = int(db_str) if db_str else 0
                        else:
                            host_port = host_part
                            db = 0
                        host, port_str = host_port.rsplit(":", 1)
                        port = int(port_str)
                        logger.info(f"[WebSocket] Connecting to Redis at {host}:{port} db={db}")
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
                        logger.error("[WebSocket] Invalid Redis URL format")
                        return None
                else:
                    self._redis = aioredis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info("[WebSocket] Connected to Redis")
            except Exception as e:
                logger.error(f"[WebSocket] Failed to connect to Redis: {e}")
                self._redis = None
        return self._redis

    async def start_listener(self):
        """Start the Redis pub/sub listener."""
        redis_client = await self._get_redis()
        if not redis_client:
            logger.warning("[WebSocket] Redis not available, running in single-worker mode")
            return

        try:
            self._pubsub = redis_client.pubsub()
            await self._pubsub.subscribe(REDIS_CHANNEL)
            self._listener_task = asyncio.create_task(self._listen_to_redis())
            logger.info("[WebSocket] Redis listener started")
        except Exception as e:
            logger.error(f"[WebSocket] Failed to start Redis listener: {e}")

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
                        logger.warning("[WebSocket] Invalid JSON from Redis")
                    except Exception as e:
                        logger.error(f"[WebSocket] Error processing Redis message: {e}")
        except asyncio.CancelledError:
            logger.info("[WebSocket] Redis listener stopped")
        except Exception as e:
            logger.error(f"[WebSocket] Redis listener error: {e}")

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
        logger.info("[WebSocket] Redis listener stopped")

    async def connect(self, websocket: WebSocket, tenant_id: str):
        """Accept a new WebSocket connection for a tenant."""
        await websocket.accept()
        async with self._lock:
            if tenant_id not in self._connections:
                self._connections[tenant_id] = set()
            self._connections[tenant_id].add(websocket)
        logger.info(f"[WebSocket] Client connected for tenant: {tenant_id}")

    async def disconnect(self, websocket: WebSocket, tenant_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if tenant_id in self._connections:
                self._connections[tenant_id].discard(websocket)
                if not self._connections[tenant_id]:
                    del self._connections[tenant_id]
        logger.info(f"[WebSocket] Client disconnected for tenant: {tenant_id}")

    def register_document(self, document_id: str, tenant_id: str):
        """Register a document for progress tracking."""
        self._document_tenants[document_id] = tenant_id
        logger.info(f"[WebSocket] Registered document {document_id} for tenant {tenant_id}")

    def unregister_document(self, document_id: str):
        """Unregister a document from progress tracking."""
        if document_id in self._document_tenants:
            del self._document_tenants[document_id]

    async def broadcast_progress(
        self,
        document_id: str,
        step: int,
        step_name: str,
        progress: int,
        status: str = "processing",
        error_message: str = None
    ):
        """
        Broadcast progress update to all connected clients for the document's tenant.
        Publishes to Redis so all workers can receive and forward to their connections.

        Args:
            document_id: The document being processed
            step: Current step number (1-5)
            step_name: Human-readable step name
            progress: Progress percentage (0-100)
            status: processing, completed, or failed
            error_message: Error message if failed
        """
        tenant_id = self._document_tenants.get(document_id)

        # Fallback to DB lookup if not in memory (multi-worker scenario)
        if not tenant_id:
            tenant_id = _get_tenant_from_db(document_id)
            if tenant_id:
                # Cache it for future updates
                self._document_tenants[document_id] = tenant_id
                logger.info(f"[WebSocket] Resolved tenant {tenant_id} from DB for document {document_id}")

        if not tenant_id:
            logger.warning(f"[WebSocket] No tenant found for document: {document_id}")
            return

        message = {
            "type": "progress",
            "document_id": document_id,
            "step": step,
            "step_name": step_name,
            "progress": progress,
            "status": status,
        }
        if error_message:
            message["error_message"] = error_message

        logger.info(f"[WebSocket] Broadcasting progress for document {document_id}: step={step}, progress={progress}%, status={status}")

        # Cache progress in Redis for retrieval when user returns to page
        await self._cache_progress(document_id, message)

        # Publish to Redis for all workers to receive
        await self._publish_to_redis(tenant_id, message)

    async def _cache_progress(self, document_id: str, progress_data: dict):
        """Cache progress data in Redis for retrieval when user returns."""
        redis_client = await self._get_redis()
        if redis_client:
            try:
                key = f"{REDIS_PROGRESS_PREFIX}{document_id}"
                await redis_client.setex(key, REDIS_PROGRESS_TTL, json.dumps(progress_data))
                logger.info(f"[WebSocket] Cached progress for document {document_id}: step={progress_data.get('step')}, progress={progress_data.get('progress')}%")
            except Exception as e:
                logger.warning(f"[WebSocket] Failed to cache progress: {e}")
        else:
            logger.warning(f"[WebSocket] Redis not available, cannot cache progress for document {document_id}")

    async def get_cached_progress(self, document_id: str) -> Optional[dict]:
        """Retrieve cached progress for a document."""
        redis_client = await self._get_redis()
        if redis_client:
            try:
                key = f"{REDIS_PROGRESS_PREFIX}{document_id}"
                data = await redis_client.get(key)
                if data:
                    progress = json.loads(data)
                    logger.info(f"[WebSocket] Retrieved cached progress for {document_id}: step={progress.get('step')}, progress={progress.get('progress')}%")
                    return progress
                else:
                    logger.info(f"[WebSocket] No cached progress found for {document_id}")
            except Exception as e:
                logger.warning(f"[WebSocket] Failed to get cached progress: {e}")
        else:
            logger.warning(f"[WebSocket] Redis not available, cannot retrieve cached progress")
        return None

    async def get_cached_progress_batch(self, document_ids: list) -> dict:
        """Retrieve cached progress for multiple documents."""
        results = {}
        logger.info(f"[WebSocket] Getting cached progress batch for {len(document_ids)} document(s)")
        redis_client = await self._get_redis()
        if redis_client and document_ids:
            try:
                keys = [f"{REDIS_PROGRESS_PREFIX}{doc_id}" for doc_id in document_ids]
                logger.info(f"[WebSocket] Fetching keys: {keys}")
                values = await redis_client.mget(keys)
                for doc_id, value in zip(document_ids, values):
                    if value:
                        results[doc_id] = json.loads(value)
                        logger.info(f"[WebSocket] Found cached progress for {doc_id}")
                    else:
                        logger.info(f"[WebSocket] No cached progress for {doc_id}")
                logger.info(f"[WebSocket] Batch result: {len(results)} document(s) with cached progress")
            except Exception as e:
                logger.warning(f"[WebSocket] Failed to get cached progress batch: {e}")
        else:
            if not redis_client:
                logger.warning(f"[WebSocket] Redis not available for batch progress retrieval")
        return results

    async def clear_cached_progress(self, document_id: str):
        """Clear cached progress when processing completes or fails."""
        redis_client = await self._get_redis()
        if redis_client:
            try:
                key = f"{REDIS_PROGRESS_PREFIX}{document_id}"
                await redis_client.delete(key)
                logger.debug(f"[WebSocket] Cleared cached progress for document {document_id}")
            except Exception as e:
                logger.warning(f"[WebSocket] Failed to clear cached progress: {e}")

    async def _publish_to_redis(self, tenant_id: str, payload: dict):
        """Publish a message to Redis channel."""
        redis_client = await self._get_redis()
        if redis_client:
            try:
                message = json.dumps({"tenant_id": tenant_id, "payload": payload})
                await redis_client.publish(REDIS_CHANNEL, message)
                logger.info(f"[WebSocket] Published to Redis for tenant {tenant_id}")
            except Exception as e:
                logger.error(f"[WebSocket] Failed to publish to Redis: {e}")
                # Fallback to local send if Redis fails
                logger.info(f"[WebSocket] Falling back to local send for tenant {tenant_id}")
                await self._send_to_tenant(tenant_id, payload)
        else:
            # No Redis, send directly (single-worker mode)
            logger.info(f"[WebSocket] No Redis configured, sending directly to tenant {tenant_id}")
            await self._send_to_tenant(tenant_id, payload)

    async def _send_to_tenant(self, tenant_id: str, message: dict):
        """Send a message to all connections for a tenant."""
        if tenant_id not in self._connections:
            logger.warning(f"[WebSocket] No connections found for tenant: {tenant_id}. Active tenants: {list(self._connections.keys())}")
            return

        connection_count = len(self._connections[tenant_id])
        logger.info(f"[WebSocket] Sending message to {connection_count} connection(s) for tenant {tenant_id}")

        dead_connections = set()
        sent_count = 0

        for websocket in list(self._connections[tenant_id]):  # Copy to list to allow modification
            try:
                # Add timeout to prevent blocking on dead connections
                await asyncio.wait_for(
                    websocket.send_json(message),
                    timeout=5.0  # 5 second timeout per connection
                )
                sent_count += 1
                logger.info(f"[WebSocket] Message sent successfully to connection {sent_count}/{connection_count}")
            except asyncio.TimeoutError:
                logger.warning(f"[WebSocket] Timeout sending to connection - marking as dead")
                dead_connections.add(websocket)
            except Exception as e:
                logger.warning(f"[WebSocket] Failed to send message: {e}")
                dead_connections.add(websocket)

        logger.info(f"[WebSocket] Sent to {sent_count}/{connection_count} connections, {len(dead_connections)} dead")

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
ws_manager = DocumentWebSocketManager()
