"""
Carbon Voice Connector Client.
Handles OAuth2 authentication, token management, and API calls.
"""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urlencode

from config.settings import (
    CARBONVOICE_CLIENT_ID,
    CARBONVOICE_CLIENT_SECRET,
    CARBONVOICE_REDIRECT_URI,
)
from database.models.connector import ConnectorConfig
from utils.logger import get_logger

logger = get_logger(__name__)


# Carbon Voice API URLs
CV_API_BASE_URL = "https://api.carbonvoice.app"
CV_OAUTH_AUTHORIZE_URL = f"{CV_API_BASE_URL}/oauth/authorize"
CV_TOKEN_URL = f"{CV_API_BASE_URL}/oauth/token"
CV_USERINFO_URL = f"{CV_API_BASE_URL}/oauth/userinfo"

# OAuth Scopes - standard OAuth2 scopes
CV_SCOPES = [
    "openid",
    "profile",
]


@dataclass
class CarbonVoiceEntityDefinition:
    """Definition of a Carbon Voice entity that can be synced"""
    entity_key: str
    api_endpoint: str
    display_name: str
    description: str
    default_enabled: bool
    pillar_hint: str


# Supported Carbon Voice entities
CARBONVOICE_ENTITIES: List[CarbonVoiceEntityDefinition] = [
    CarbonVoiceEntityDefinition(
        entity_key="workspace",
        api_endpoint="/v5/workspaces",
        display_name="Workspaces",
        description="Workspaces grouping people and conversations",
        default_enabled=True,
        pillar_hint="operational_maturity",
    ),
    CarbonVoiceEntityDefinition(
        entity_key="channel",
        api_endpoint="/channels/{workspace_guid}",
        display_name="Channels (Conversations)",
        description="Communication channels within workspaces",
        default_enabled=True,
        pillar_hint="customer_health",
    ),
    CarbonVoiceEntityDefinition(
        entity_key="message",
        api_endpoint="/v3/messages/{channel_id}/sequential/{start}/{stop}",
        display_name="Messages (Discussions)",
        description="Individual messages and voice posts",
        default_enabled=True,
        pillar_hint="customer_health",
    ),
    CarbonVoiceEntityDefinition(
        entity_key="action_item",
        api_endpoint="/action-items/{container_type}/{container_id}",
        display_name="Action Items",
        description="Tasks and action items from conversations",
        default_enabled=True,
        pillar_hint="operational_maturity",
    ),
]

CARBONVOICE_ENTITY_MAP: Dict[str, CarbonVoiceEntityDefinition] = {
    e.entity_key: e for e in CARBONVOICE_ENTITIES
}


class CarbonVoiceConnector:
    """
    Carbon Voice connector for OAuth and API operations.
    """

    def __init__(self, config: Optional[ConnectorConfig] = None):
        """
        Initialize Carbon Voice connector.

        Args:
            config: Optional ConnectorConfig record. If provided, uses stored tokens.
        """
        self.config = config
        self.client_id = CARBONVOICE_CLIENT_ID
        self.client_secret = CARBONVOICE_CLIENT_SECRET
        self.redirect_uri = CARBONVOICE_REDIRECT_URI
        self.api_base_url = CV_API_BASE_URL

    def is_configured(self) -> bool:
        """Check if Carbon Voice credentials are configured"""
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    # =========================================================================
    # OAuth Methods
    # =========================================================================

    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth2 authorization URL for user to connect Carbon Voice.

        Args:
            state: Random state string for CSRF protection (store in session)

        Returns:
            URL to redirect user to for Carbon Voice authorization
        """
        if not self.is_configured():
            raise ValueError("Carbon Voice credentials not configured")

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": " ".join(CV_SCOPES),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        return f"{CV_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict with access_token, refresh_token, expires_in, etc.
        """
        if not self.is_configured():
            raise ValueError("Carbon Voice credentials not configured")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(CV_TOKEN_URL, headers=headers, data=data)

            if response.status_code != 200:
                logger.error(f"[CarbonVoice] Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.text}")

            token_data = response.json()
            logger.info("[CarbonVoice] Successfully exchanged code for tokens")
            return token_data

    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using the refresh token.

        Returns:
            Dict with new access_token, refresh_token, expires_in, etc.

        Raises:
            ValueError: If no config or refresh token available
        """
        if not self.config or not self.config.refresh_token:
            raise ValueError("No refresh token available")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(CV_TOKEN_URL, headers=headers, data=data)

            if response.status_code != 200:
                logger.error(f"[CarbonVoice] Token refresh failed: {response.text}")
                raise ValueError(f"Token refresh failed: {response.text}")

            token_data = response.json()
            logger.info("[CarbonVoice] Successfully refreshed access token")
            return token_data

    # =========================================================================
    # API Helper Methods
    # =========================================================================

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API calls"""
        if not self.config or not self.config.access_token:
            raise ValueError("No access token available")

        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _make_api_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Make an authenticated API request to Carbon Voice.

        Args:
            endpoint: API endpoint (relative to base URL)
            method: HTTP method
            params: Query parameters
            json_data: JSON body data
            timeout: Request timeout in seconds

        Returns:
            JSON response data
        """
        url = f"{self.api_base_url}{endpoint}"
        headers = self._get_auth_headers()

        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, params=params, json=json_data)
            elif method == "PUT":
                response = await client.put(url, headers=headers, params=params, json=json_data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, params=params)
            else:
                response = await client.request(method, url, headers=headers, params=params, json=json_data)

            if response.status_code == 401:
                logger.warning("[CarbonVoice] Access token expired or invalid")
                raise ValueError("Access token expired")

            if response.status_code == 429:
                # Rate limited
                retry_after = response.headers.get("X-RateLimit-Reset", "60")
                logger.warning(f"[CarbonVoice] Rate limited. Retry after: {retry_after}")
                raise ValueError(f"Rate limited. Retry after {retry_after} seconds")

            if response.status_code not in [200, 201]:
                logger.error(f"[CarbonVoice] API request failed: {response.status_code} - {response.text}")
                raise ValueError(f"API request failed: {response.text}")

            return response.json()

    # =========================================================================
    # User & Account Methods
    # =========================================================================

    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get current user info from Carbon Voice.

        Returns:
            Dict with user information
        """
        return await self._make_api_request("/whoami")

    async def get_oauth_userinfo(self) -> Dict[str, Any]:
        """
        Get user info from OAuth userinfo endpoint.

        Returns:
            Dict with OAuth user information
        """
        return await self._make_api_request("/oauth/userinfo")

    # =========================================================================
    # Workspace Methods
    # =========================================================================

    async def get_workspaces(self) -> List[Dict[str, Any]]:
        """
        Fetch all workspaces for the authenticated user.

        Returns:
            List of workspace objects
        """
        data = await self._make_api_request("/v5/workspaces")
        # Handle different response formats
        if isinstance(data, list):
            return data
        # v5 endpoint returns {results: [...], next_cursor: ..., ...}
        if "results" in data:
            return data["results"]
        return data.get("workspaces", data.get("data", []))

    async def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """
        Fetch a specific workspace by ID.

        Args:
            workspace_id: Workspace GUID

        Returns:
            Workspace object
        """
        return await self._make_api_request(f"/v5/workspaces/{workspace_id}")

    async def discover_available_entities(self) -> List[Dict[str, Any]]:
        """
        Discover what entities are available and their counts.

        Returns:
            List of entity info dicts with counts and availability
        """
        available_entities = []

        for entity_def in CARBONVOICE_ENTITIES:
            entity_info = {
                "entity_key": entity_def.entity_key,
                "display_name": entity_def.display_name,
                "description": entity_def.description,
                "default_enabled": entity_def.default_enabled,
                "pillar_hint": entity_def.pillar_hint,
                "record_count": None,
                "is_available": False,
                "error": None,
            }

            try:
                if entity_def.entity_key == "workspace":
                    workspaces = await self.get_workspaces()
                    entity_info["record_count"] = len(workspaces)
                    entity_info["is_available"] = len(workspaces) > 0
                elif entity_def.entity_key == "channel":
                    # Get total channels across all workspaces
                    workspaces = await self.get_workspaces()
                    total_channels = 0
                    for ws in workspaces[:5]:  # Limit to first 5 for discovery
                        ws_id = ws.get("workspace_guid") or ws.get("id")
                        if ws_id:
                            try:
                                channels = await self.get_channels(ws_id)
                                total_channels += len(channels)
                            except Exception:
                                pass
                    entity_info["record_count"] = total_channels
                    entity_info["is_available"] = total_channels > 0
                else:
                    # For messages and action items, just mark as available if workspaces exist
                    workspaces = await self.get_workspaces()
                    entity_info["is_available"] = len(workspaces) > 0
                    entity_info["record_count"] = None  # Unknown count

            except Exception as e:
                logger.warning(f"[CarbonVoice] Could not check entity {entity_def.entity_key}: {e}")
                entity_info["error"] = str(e)
                entity_info["is_available"] = False

            available_entities.append(entity_info)

        logger.info(f"[CarbonVoice] Discovered {len(available_entities)} entities")
        return available_entities

    # =========================================================================
    # Channel (Conversation) Methods
    # =========================================================================

    async def get_channels(self, workspace_guid: str) -> List[Dict[str, Any]]:
        """
        Fetch channels (conversations) for a workspace.

        Args:
            workspace_guid: Workspace GUID

        Returns:
            List of channel objects
        """
        data = await self._make_api_request(f"/channels/{workspace_guid}")
        if isinstance(data, list):
            return data
        return data.get("channels", data.get("data", []))

    async def get_channel(self, channel_guid: str) -> Dict[str, Any]:
        """
        Fetch a specific channel by ID.

        Args:
            channel_guid: Channel GUID

        Returns:
            Channel object
        """
        return await self._make_api_request(f"/v2/channel/{channel_guid}")

    async def get_channel_summary(self, channel_id: str) -> Dict[str, Any]:
        """
        Get AI-generated summary of a conversation.

        Args:
            channel_id: Channel ID

        Returns:
            Summary object
        """
        return await self._make_api_request(f"/channels/{channel_id}/summary")

    # =========================================================================
    # Message (Discussion) Methods
    # =========================================================================

    async def get_messages(
        self,
        channel_id: str,
        start: int = 0,
        stop: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages for a channel using sequence numbers.

        Args:
            channel_id: Channel ID
            start: Start sequence number
            stop: Stop sequence number

        Returns:
            List of message objects
        """
        data = await self._make_api_request(
            f"/v3/messages/{channel_id}/sequential/{start}/{stop}"
        )
        if isinstance(data, list):
            return data
        return data.get("messages", data.get("data", []))

    async def get_messages_by_ids(self, message_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch messages by their IDs (batch request, up to 500).

        Args:
            message_ids: List of message IDs

        Returns:
            List of message objects
        """
        data = await self._make_api_request(
            "/v5/messages/by-ids",
            method="POST",
            json_data={"message_ids": message_ids[:500]}  # API limit
        )
        if isinstance(data, list):
            return data
        return data.get("messages", data.get("data", []))

    async def get_recent_messages(
        self,
        channel_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent messages.

        Args:
            channel_id: Optional channel ID to filter
            limit: Maximum number of messages

        Returns:
            List of message objects
        """
        payload = {"limit": limit}
        if channel_id:
            payload["channel_id"] = channel_id

        data = await self._make_api_request(
            "/v3/messages/recent",
            method="POST",
            json_data=payload
        )
        if isinstance(data, list):
            return data
        return data.get("messages", data.get("data", []))

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Fetch a specific message by ID.

        Args:
            message_id: Message ID

        Returns:
            Message object
        """
        return await self._make_api_request(f"/v5/messages/{message_id}")

    # =========================================================================
    # Action Items Methods
    # =========================================================================

    async def get_action_items(
        self,
        container_type: str,
        container_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch action items for a container (workspace/channel).

        Args:
            container_type: Container type (e.g., "workspace", "channel")
            container_id: Container ID

        Returns:
            List of action item objects
        """
        data = await self._make_api_request(
            f"/action-items/{container_type}/{container_id}"
        )
        if isinstance(data, list):
            return data
        return data.get("action_items", data.get("data", []))

    async def get_my_action_items(self) -> List[Dict[str, Any]]:
        """
        Fetch action items assigned to the current user.

        Returns:
            List of action item objects
        """
        data = await self._make_api_request("/action-items/mine")
        if isinstance(data, list):
            return data
        return data.get("action_items", data.get("data", []))

    # =========================================================================
    # Search Methods
    # =========================================================================

    async def search_messages(
        self,
        query: str,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search messages across workspaces.

        Args:
            query: Search query
            workspace_id: Optional workspace to search within

        Returns:
            List of search results
        """
        payload = {"query": query}
        if workspace_id:
            payload["workspace_id"] = workspace_id

        data = await self._make_api_request(
            "/v3/search",
            method="POST",
            json_data=payload
        )
        if isinstance(data, list):
            return data
        return data.get("results", data.get("data", []))

    # =========================================================================
    # Data Export Methods
    # =========================================================================

    async def export_conversations(
        self,
        conversation_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Start data export for conversations.

        Args:
            conversation_ids: List of conversation/channel IDs to export

        Returns:
            Export job info
        """
        return await self._make_api_request(
            "/data-exporter/conversations",
            method="POST",
            json_data={"conversation_ids": conversation_ids}
        )

    async def get_export_status(self, export_id: str) -> Dict[str, Any]:
        """
        Get status of a data export job.

        Args:
            export_id: Export job ID

        Returns:
            Export status info
        """
        return await self._make_api_request(f"/data-exporter/{export_id}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @staticmethod
    def get_supported_entities() -> List[Dict[str, Any]]:
        """
        Get list of all supported Carbon Voice entities.
        This is static - doesn't require a connection.

        Returns:
            List of entity definitions
        """
        return [
            {
                "entity_key": e.entity_key,
                "api_endpoint": e.api_endpoint,
                "display_name": e.display_name,
                "description": e.description,
                "default_enabled": e.default_enabled,
                "pillar_hint": e.pillar_hint,
            }
            for e in CARBONVOICE_ENTITIES
        ]

    def get_entity_external_id(self, entity_key: str, record: Dict[str, Any]) -> Optional[str]:
        """Extract the Carbon Voice ID from a record"""
        # Different entities have different ID fields
        id_fields = ["id", "workspace_guid", "channel_guid", "message_guid", "_id"]
        for field in id_fields:
            if field in record:
                return str(record[field])
        return None

    def get_entity_updated_at(self, entity_key: str, record: Dict[str, Any]) -> Optional[datetime]:
        """Extract the last modified timestamp from a record"""
        # Try various timestamp fields
        ts_fields = ["last_updated_ts", "updated_at", "created_at", "last_seen_ts"]

        for field in ts_fields:
            if field in record:
                ts_value = record[field]
                if isinstance(ts_value, (int, float)):
                    # Unix timestamp (milliseconds or seconds)
                    if ts_value > 1e12:  # Milliseconds
                        return datetime.utcfromtimestamp(ts_value / 1000)
                    else:  # Seconds
                        return datetime.utcfromtimestamp(ts_value)
                elif isinstance(ts_value, str):
                    try:
                        return datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
                    except ValueError:
                        pass

        return None
