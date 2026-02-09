"""
WebSocket manager for scoring pipeline progress updates.
Uses Redis pub/sub for multi-worker support.
"""
import asyncio
import json
from typing import Dict, Set, Optional, List
from fastapi import WebSocket
from utils.logger import get_logger
from config.settings import AZURE_REDIS_CONNECTION_STRING

logger = get_logger(__name__)

# Redis channel for scoring WebSocket messages
SCORING_REDIS_CHANNEL = "websocket:scoring_progress"

# All 8 BDE pillars
BDE_PILLARS = [
    "financial_health",
    "gtm_engine",
    "customer_health",
    "product_technical",
    "operational_maturity",
    "leadership_transition",
    "ecosystem_dependency",
    "service_software_ratio",
]

# Pillar display names
PILLAR_NAMES = {
    "financial_health": "Financial Health",
    "gtm_engine": "GTM Engine",
    "customer_health": "Customer Health",
    "product_technical": "Product/Technical",
    "operational_maturity": "Operational Maturity",
    "leadership_transition": "Leadership Transition",
    "ecosystem_dependency": "Ecosystem Dependency",
    "service_software_ratio": "Service/Software Ratio",
}

# Scoring pipeline stages with weights for progress calculation
SCORING_STAGES = {
    1: {"name": "Extracting Metrics", "weight": 20},
    2: {"name": "Aggregating Pillar Data", "weight": 10},
    3: {"name": "Evaluating & Scoring Pillars", "weight": 40},  # Per-pillar progress shown here
    4: {"name": "Detecting Flags", "weight": 15},
    5: {"name": "Calculating BDE Score & Recommendation", "weight": 15},
}


class ScoringWebSocketManager:
    """
    Manages WebSocket connections for scoring pipeline progress updates.
    One connection per user, broadcasts progress for their scoring jobs.
    Uses Redis pub/sub for multi-worker support.
    Shows per-pillar progress during evaluation stage.
    """

    def __init__(self):
        # Map: tenant_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Map: company_id -> tenant_id (for routing progress updates)
        self._company_tenants: Dict[str, str] = {}
        # Map: company_id -> last scored document count (for rerun check)
        self._last_scored_doc_counts: Dict[str, int] = {}
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
                logger.error("[ScoringWS] AZURE_REDIS_CONNECTION_STRING not set")
                return None
            try:
                # For Azure Redis SSL connections, pass password explicitly
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
                        logger.info(f"[ScoringWS] Connecting to Redis at {host}:{port} db={db}")
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
                        logger.error("[ScoringWS] Invalid Redis URL format")
                        return None
                else:
                    self._redis = aioredis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info("[ScoringWS] Connected to Redis")
            except Exception as e:
                logger.error(f"[ScoringWS] Failed to connect to Redis: {e}")
                self._redis = None
        return self._redis

    async def start_listener(self):
        """Start the Redis pub/sub listener."""
        redis_client = await self._get_redis()
        if not redis_client:
            logger.warning("[ScoringWS] Redis not available, running in single-worker mode")
            return

        try:
            self._pubsub = redis_client.pubsub()
            await self._pubsub.subscribe(SCORING_REDIS_CHANNEL)
            self._listener_task = asyncio.create_task(self._listen_to_redis())
            logger.info("[ScoringWS] Redis listener started")
        except Exception as e:
            logger.error(f"[ScoringWS] Failed to start Redis listener: {e}")

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
                        logger.warning("[ScoringWS] Invalid JSON from Redis")
                    except Exception as e:
                        logger.error(f"[ScoringWS] Error processing Redis message: {e}")
        except asyncio.CancelledError:
            logger.info("[ScoringWS] Redis listener stopped")
        except Exception as e:
            logger.error(f"[ScoringWS] Redis listener error: {e}")

    async def stop_listener(self):
        """Stop the Redis pub/sub listener."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe(SCORING_REDIS_CHANNEL)
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("[ScoringWS] Redis listener stopped")

    async def connect(self, websocket: WebSocket, tenant_id: str):
        """Accept a new WebSocket connection for a tenant."""
        await websocket.accept()
        async with self._lock:
            if tenant_id not in self._connections:
                self._connections[tenant_id] = set()
            self._connections[tenant_id].add(websocket)
        logger.info(f"[ScoringWS] Client connected for tenant: {tenant_id}")

    async def disconnect(self, websocket: WebSocket, tenant_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if tenant_id in self._connections:
                self._connections[tenant_id].discard(websocket)
                if not self._connections[tenant_id]:
                    del self._connections[tenant_id]
        logger.info(f"[ScoringWS] Client disconnected for tenant: {tenant_id}")

    def register_company(self, company_id: str, tenant_id: str, doc_count: int = 0):
        """Register a company for scoring progress tracking."""
        self._company_tenants[company_id] = tenant_id
        self._last_scored_doc_counts[company_id] = doc_count
        logger.info(f"[ScoringWS] Registered company {company_id} for tenant {tenant_id}, doc_count={doc_count}")

    def unregister_company(self, company_id: str):
        """Unregister a company from progress tracking."""
        if company_id in self._company_tenants:
            del self._company_tenants[company_id]

    def get_last_scored_doc_count(self, company_id: str) -> int:
        """Get the document count when scoring was last run."""
        return self._last_scored_doc_counts.get(company_id, 0)

    def update_last_scored_doc_count(self, company_id: str, doc_count: int):
        """Update the document count after scoring completes."""
        self._last_scored_doc_counts[company_id] = doc_count

    async def broadcast_progress(
        self,
        company_id: str,
        stage: int,
        stage_name: str,
        progress: int,
        status: str = "processing",
        current_pillar: str = None,
        pillar_progress: Dict[str, dict] = None,
        error_message: str = None,
        result: dict = None
    ):
        """
        Broadcast scoring progress update to all connected clients for the company's tenant.

        Args:
            company_id: The company being scored
            stage: Current stage number (1-5)
            stage_name: Human-readable stage name
            progress: Overall progress percentage (0-100)
            status: processing, completed, or failed
            current_pillar: Current pillar being processed (if applicable)
            pillar_progress: Dict of pillar -> {status, progress, score, health_status}
                - status: 'pending', 'processing', 'completed'
                - progress: 0-100 for this pillar
                - score: final score (if completed)
                - health_status: 'green', 'yellow', 'red' (if completed)
            error_message: Error message if failed
            result: Final scoring result (if completed)
        """
        tenant_id = self._company_tenants.get(company_id)

        if not tenant_id:
            # Try to get from DB
            tenant_id = self._get_tenant_from_db(company_id)
            if tenant_id:
                self._company_tenants[company_id] = tenant_id

        if not tenant_id:
            logger.warning(f"[ScoringWS] No tenant found for company: {company_id}")
            return

        message = {
            "type": "scoring_progress",
            "company_id": company_id,
            "stage": stage,
            "stage_name": stage_name,
            "progress": progress,
            "status": status,
            "current_pillar": current_pillar,
            "pillar_progress": pillar_progress or self._get_initial_pillar_progress(),
        }
        if error_message:
            message["error_message"] = error_message
        if result:
            message["result"] = result

        await self._publish_to_redis(tenant_id, message)

    def _get_initial_pillar_progress(self) -> Dict[str, dict]:
        """Get initial pillar progress state (all pending)."""
        return {
            pillar: {
                "name": PILLAR_NAMES[pillar],
                "status": "pending",
                "progress": 0,
                "score": None,
                "health_status": None,
            }
            for pillar in BDE_PILLARS
        }

    def _get_tenant_from_db(self, company_id: str) -> Optional[str]:
        """Lookup tenant_id from database for a company."""
        try:
            from database.connection import engine
            from sqlmodel import Session
            from database.models import Company

            with Session(engine) as session:
                company = session.get(Company, company_id)
                if company:
                    return company.tenant_id
        except Exception as e:
            logger.error(f"[ScoringWS] Failed to lookup tenant from DB: {e}")
        return None

    async def _publish_to_redis(self, tenant_id: str, payload: dict):
        """Publish a message to Redis channel."""
        redis_client = await self._get_redis()
        if redis_client:
            try:
                message = json.dumps({"tenant_id": tenant_id, "payload": payload})
                await redis_client.publish(SCORING_REDIS_CHANNEL, message)
                logger.debug(f"[ScoringWS] Published to Redis for tenant {tenant_id}")
            except Exception as e:
                logger.error(f"[ScoringWS] Failed to publish to Redis: {e}")
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
                logger.warning(f"[ScoringWS] Failed to send message: {e}")
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
scoring_ws_manager = ScoringWebSocketManager()
