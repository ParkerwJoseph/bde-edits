import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket
from utils.logger import get_logger
from config.settings import AZURE_REDIS_CONNECTION_STRING

logger = get_logger(__name__)

# Redis channel for chat WebSocket messages
REDIS_CHAT_CHANNEL = "websocket:chat"


class ChatWebSocketManager:
    """
    Manages WebSocket connections for chat streaming.
    Uses Redis pub/sub for multi-worker support (5 workers).

    Message types sent to client:
    - {"type": "status", "phase": "searching"} - Searching documents
    - {"type": "status", "phase": "generating"} - Found sources, generating response
    - {"type": "session", "session_id": "..."} - Session created
    - {"type": "sources", "data": {...}} - Sources found
    - {"type": "chunk", "data": "..."} - Text chunk
    - {"type": "done"} - Stream complete
    - {"type": "error", "message": "..."} - Error occurred
    """

    def __init__(self):
        # Map: user_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Map: request_id -> user_id (for routing responses)
        self._request_users: Dict[str, str] = {}
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
                logger.error("[ChatWS] AZURE_REDIS_CONNECTION_STRING not set")
                return None
            try:
                if redis_url.startswith("rediss://"):
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
                        logger.info(f"[ChatWS] Connecting to Redis at {host}:{port} db={db}")
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
                        logger.error("[ChatWS] Invalid Redis URL format")
                        return None
                else:
                    self._redis = aioredis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info("[ChatWS] Connected to Redis")
            except Exception as e:
                logger.error(f"[ChatWS] Failed to connect to Redis: {e}")
                self._redis = None
        return self._redis

    async def start_listener(self):
        """Start the Redis pub/sub listener."""
        redis_client = await self._get_redis()
        if not redis_client:
            logger.warning("[ChatWS] Redis not available, running in single-worker mode")
            return

        try:
            self._pubsub = redis_client.pubsub()
            await self._pubsub.subscribe(REDIS_CHAT_CHANNEL)
            self._listener_task = asyncio.create_task(self._listen_to_redis())
            logger.info("[ChatWS] Redis listener started")
        except Exception as e:
            logger.error(f"[ChatWS] Failed to start Redis listener: {e}")

    async def _listen_to_redis(self):
        """Listen for messages from Redis and forward to local WebSocket connections."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        user_id = data.get("user_id")
                        payload = data.get("payload")
                        if user_id and payload:
                            await self._send_to_user(user_id, payload)
                    except json.JSONDecodeError:
                        logger.warning("[ChatWS] Invalid JSON from Redis")
                    except Exception as e:
                        logger.error(f"[ChatWS] Error processing Redis message: {e}")
        except asyncio.CancelledError:
            logger.info("[ChatWS] Redis listener stopped")
        except Exception as e:
            logger.error(f"[ChatWS] Redis listener error: {e}")

    async def stop_listener(self):
        """Stop the Redis pub/sub listener."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe(REDIS_CHAT_CHANNEL)
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("[ChatWS] Redis listener stopped")

    async def connect(self, websocket: WebSocket, user_id: str):
        """Register a WebSocket connection for a user (websocket should already be accepted)."""
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(websocket)
        logger.info(f"[ChatWS] Client connected for user: {user_id}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info(f"[ChatWS] Client disconnected for user: {user_id}")

    def register_request(self, request_id: str, user_id: str):
        """Register a chat request for routing responses."""
        self._request_users[request_id] = user_id

    def unregister_request(self, request_id: str):
        """Unregister a chat request."""
        if request_id in self._request_users:
            del self._request_users[request_id]

    async def send_status(self, user_id: str, phase: str, message: str = None):
        """Send a status update (searching, generating, etc.)."""
        payload = {"type": "status", "phase": phase}
        if message:
            payload["message"] = message
        await self._publish_to_redis(user_id, payload)

    async def send_session(self, user_id: str, session_id: str):
        """Send session ID."""
        await self._publish_to_redis(user_id, {
            "type": "session",
            "session_id": session_id
        })

    async def send_sources(self, user_id: str, sources: list, chunks: list = None):
        """Send sources found."""
        await self._publish_to_redis(user_id, {
            "type": "sources",
            "data": {"sources": sources, "chunks": chunks or []}
        })

    async def send_chunk(self, user_id: str, chunk: str):
        """Send a text chunk."""
        await self._publish_to_redis(user_id, {
            "type": "chunk",
            "data": chunk
        })

    async def send_done(self, user_id: str):
        """Send done signal."""
        await self._publish_to_redis(user_id, {"type": "done"})

    async def send_error(self, user_id: str, error_message: str):
        """Send error message."""
        await self._publish_to_redis(user_id, {
            "type": "error",
            "message": error_message
        })

    async def _publish_to_redis(self, user_id: str, payload: dict):
        """Publish a message to Redis channel."""
        redis_client = await self._get_redis()
        if redis_client:
            try:
                message = json.dumps({"user_id": user_id, "payload": payload})
                await redis_client.publish(REDIS_CHAT_CHANNEL, message)
            except Exception as e:
                logger.error(f"[ChatWS] Failed to publish to Redis: {e}")
                await self._send_to_user(user_id, payload)
        else:
            await self._send_to_user(user_id, payload)

    async def _send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections for a user."""
        if user_id not in self._connections:
            return

        dead_connections = set()
        for websocket in self._connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"[ChatWS] Failed to send message: {e}")
                dead_connections.add(websocket)

        for ws in dead_connections:
            await self.disconnect(ws, user_id)

    def get_connection_count(self, user_id: str = None) -> int:
        """Get the number of active connections."""
        if user_id:
            return len(self._connections.get(user_id, set()))
        return sum(len(conns) for conns in self._connections.values())


# Global instance
chat_ws_manager = ChatWebSocketManager()
