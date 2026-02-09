# Carbon Voice Integration Guide

## Overview

This document outlines the implementation plan for integrating Carbon Voice into the BDE web application. The integration follows the same architectural patterns established by the QuickBooks connector implementation.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Implementation Phases](#implementation-phases)
4. [File Structure](#file-structure)
5. [Configuration Setup](#configuration-setup)
6. [Backend Implementation](#backend-implementation)
7. [Frontend Implementation](#frontend-implementation)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Checklist](#deployment-checklist)

---

## Prerequisites

### Carbon Voice Developer Account

- **Developer Portal**: https://developer.carbonvoice.app
- **API Documentation**: https://api.carbonvoice.app/docs

### Credentials Obtained

| Credential | Value | Environment Variable |
|------------|-------|---------------------|
| Client ID | `hIDfX6hmcw5P6IxEG2weC77L` | `CARBONVOICE_CLIENT_ID` |
| Client Secret | `ZWAG3sPI9K2SAYzs6pvisMqIoFDoRnq1NUtzv1VgqvLxRzjpIfHpwkMZav6fNOHU` | `CARBONVOICE_CLIENT_SECRET` |
| Callback URL | `http://localhost:8000/api/connectors/carbonvoice/oauth/callback` | `CARBONVOICE_REDIRECT_URI` |
| Webhook URL | `http://localhost:8000/api/connectors/carbonvoice/webhook` | (configured in Carbon Voice dashboard) |

### OAuth2 Configuration (Confirmed from API Docs)

| Setting | Value |
|---------|-------|
| **Base URL** | `https://api.carbonvoice.app` |
| **Authorization URL** | `https://api.carbonvoice.app/oauth/authorize` |
| **Token URL** | `https://api.carbonvoice.app/oauth/token` |
| **User Info URL** | `https://api.carbonvoice.app/oauth/userinfo` |
| **Well-Known Metadata** | `https://api.carbonvoice.app/.well-known/oauth-authorization-server` |

> **Note**: Rate limiting applies. Check `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.

### Carbon Voice Terminology

| Term | Description |
|------|-------------|
| **Workspace** | An area that groups together people and Conversations |
| **Conversation** | A channel of communication; grouping of people and messages related to a topic |
| **Collaborators** | A group of people who are part of a Conversation |
| **Discussion** | Any post into a conversation |
| **CarbonLink** | A link (website, QR code, or phone call) to start a conversation |

### Available API Endpoints (Key Endpoints for Integration)

#### OAuth2 Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/oauth/authorize` | Start OAuth authorization flow |
| POST | `/oauth/token` | Exchange code for access token |
| GET | `/oauth/userinfo` | Get authenticated user info |
| GET | `/.well-known/oauth-authorization-server` | OAuth server metadata |

#### Workspaces
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v5/workspaces` | Get all workspaces |
| GET | `/v5/workspaces/{id}` | Get workspace by ID |
| GET | `/v3/workspaces` | Get workspaces (v3) |
| GET | `/v3/workspaces/{workspaceguid}` | Get workspace by GUID |
| POST | `/v3/workspace` | Create workspace |

#### Channels (Conversations)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/channels/{workspaceguid}` | Get workspace channels |
| GET | `/channels/{workspaceguid}/available` | Get available channels |
| GET | `/v2/channel/{channelguid}` | Get channel by ID |
| GET | `/channel/{channelguid}` | Get channel by ID |
| GET | `/channel/collaborators/{workspaceguid}/{channelguid}` | Get channel collaborators |
| GET | `/channels/{channel_id}/summary` | Get AI summary of conversation |

#### Messages (Discussions)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v5/messages/{id}` | Get message by ID |
| POST | `/v5/messages/by-ids` | Get messages by IDs (batch) |
| GET | `/v3/messages/{channel_id}/by-id` | Get messages by channel |
| GET | `/v3/messages/{channel_id}/sequential/{start}/{stop}` | Get messages by sequence |
| POST | `/v3/messages/recent` | Get recent messages |
| POST | `/v3/search` | Search messages |
| GET | `/v5/conversations/{id}/messages/ids` | List message IDs |

#### CarbonLinks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/carbonlink/create` | Create a CarbonLink |
| POST | `/carbonlink/personal` | Create personal CarbonLink |

#### User & Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/whoami` | Get current user info |
| GET | `/users` | Get users |
| GET | `/users/last-seen` | Get last seen info |

#### Action Items
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/action-items/{container_type}/{container_id}` | List action items |
| GET | `/action-items/mine` | Get my action items |
| POST | `/action-items` | Create action item |

#### Data Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/data-exporter/conversations` | Export conversations data |
| POST | `/data-exporter/users` | Export users data |
| GET | `/data-exporter/{id}` | Get export status |

---

## Architecture Overview

### Authentication Flow

Carbon Voice supports three authentication methods:
1. **OAuth2 Access Token** (Bearer) - **RECOMMENDED** ✅
2. Client ID and Client Secret
3. PXToken

We will use **OAuth2 Access Token** authentication to maintain consistency with the QuickBooks implementation and follow security best practices.

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OAUTH FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Frontend          API Server              Carbon Voice                      │
│     │                  │                        │                            │
│     │──(1) Start OAuth─▶│                        │                            │
│     │                  │──(2) Generate State────▶│                            │
│     │◀─(3) Auth URL────│                        │                            │
│     │                  │                        │                            │
│     │══════════════(4) Redirect to Carbon Voice═══════════════▶│            │
│     │                  │                        │                            │
│     │◀═══════════════(5) User Authorizes════════════════════════│            │
│     │                  │                        │                            │
│     │──(6) Callback────▶│                        │                            │
│     │                  │──(7) Exchange Code─────▶│                            │
│     │                  │◀─(8) Access Token───────│                            │
│     │                  │                        │                            │
│     │◀─(9) Success─────│                        │                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SYNC FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Frontend          API Server         Azure Queue      Azure Function        │
│     │                  │                  │                  │               │
│     │──(1) Start Sync──▶│                  │                  │               │
│     │                  │──(2) Fetch Data from Carbon Voice───────────────▶   │
│     │                  │──(3) Store Raw Data─▶│                  │            │
│     │◀─(4) Sync Started│                  │                  │               │
│     │                  │                  │                  │               │
│     │──(5) Start Ingest─▶│                  │                  │               │
│     │                  │──(6) Queue Job────▶│                  │               │
│     │                  │                  │──(7) Process──────▶│              │
│     │                  │                  │                  │               │
│     │◀═══════════════(8) WebSocket Progress Updates═══════════│              │
│     │                  │                  │                  │               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Configuration & Setup
**Estimated Effort: Small**

- [ ] Add Carbon Voice environment variables to `config/settings.py`
- [ ] Add environment variables to `.env` and `.env.example`
- [ ] Update `ConnectorType` enum in database models
- [ ] Create Carbon Voice directory structure

### Phase 2: Backend - Core Client
**Estimated Effort: Medium**

- [ ] Create `services/connectors/carbonvoice/client.py`
  - OAuth2 authorization URL generation
  - Token exchange (code → access token)
  - Token refresh
  - Token revocation
  - API request helper methods
- [ ] Define Carbon Voice entity types and data structures

### Phase 3: Backend - API Routes
**Estimated Effort: Medium**

- [ ] Create `api/connector/carbonvoice_routes.py`
  - `GET /info` - Connector info
  - `GET /` - List connectors
  - `GET /{connector_id}` - Get connector
  - `PATCH /{connector_id}` - Update connector
  - `DELETE /{connector_id}` - Disconnect
  - `POST /oauth/start` - Start OAuth
  - `GET /oauth/callback` - Handle OAuth callback
  - `GET /{connector_id}/entities` - Discover entities
  - `POST /{connector_id}/sync` - Start sync
  - `GET /{connector_id}/sync/{sync_log_id}` - Sync status
  - `POST /{connector_id}/ingest` - Queue ingestion
  - `POST /webhook` - Receive Carbon Voice webhooks
  - `WebSocket /ws/{tenant_id}` - Real-time progress

### Phase 4: Backend - Sync & Ingestion Services
**Estimated Effort: Medium**

- [ ] Create `services/connectors/carbonvoice/sync_service.py`
  - Fetch workspaces, conversations, discussions
  - Handle pagination
  - Store raw data in database
- [ ] Create `services/connectors/carbonvoice/ingestion_service.py`
  - Process raw Carbon Voice data into chunks
  - Map to BDE pillars

### Phase 5: Azure Functions Integration
**Estimated Effort: Small**

- [ ] Add Carbon Voice queue processing to Azure Functions
- [ ] Update `queue_service.py` for Carbon Voice messages

### Phase 6: Frontend Implementation
**Estimated Effort: Medium**

- [ ] Create `frontend/src/api/carbonvoiceApi.ts`
- [ ] Add Carbon Voice connector UI components
- [ ] Update connector selection/management pages

### Phase 7: Testing & Documentation
**Estimated Effort: Small**

- [ ] Write unit tests for client methods
- [ ] Write integration tests for OAuth flow
- [ ] Test end-to-end sync and ingestion
- [ ] Update API documentation

---

## File Structure

```
web-app/
├── config/
│   └── settings.py                          # Add CARBONVOICE_* variables
│
├── services/
│   └── connectors/
│       ├── __init__.py                      # Export CarbonVoice classes
│       └── carbonvoice/
│           ├── __init__.py                  # Module exports
│           ├── client.py                    # OAuth & API client
│           ├── sync_service.py              # Data synchronization
│           └── ingestion_service.py         # Data processing/chunking
│
├── api/
│   └── connector/
│       ├── schemas.py                       # Update with CarbonVoice types
│       └── carbonvoice_routes.py            # API endpoints
│
├── database/
│   └── models/
│       └── connector.py                     # Add CARBONVOICE to ConnectorType
│
├── frontend/
│   └── src/
│       └── api/
│           └── carbonvoiceApi.ts            # Frontend API client
│
├── azure-functions/
│   └── function_app.py                      # Add CarbonVoice queue handler
│
└── docs/
    └── CARBONVOICE_INTEGRATION_GUIDE.md     # This document
```

---

## Configuration Setup

### Environment Variables

Add to `config/settings.py`:

```python
# Carbon Voice Configuration
CARBONVOICE_CLIENT_ID = os.getenv("CARBONVOICE_CLIENT_ID")
CARBONVOICE_CLIENT_SECRET = os.getenv("CARBONVOICE_CLIENT_SECRET")
CARBONVOICE_REDIRECT_URI = os.getenv("CARBONVOICE_REDIRECT_URI")
CARBONVOICE_ENVIRONMENT = os.getenv("CARBONVOICE_ENVIRONMENT", "sandbox")  # "sandbox" or "production"

# Carbon Voice Queue
CARBONVOICE_PROCESSING_QUEUE = os.getenv("CARBONVOICE_PROCESSING_QUEUE", "carbonvoice-processing")
```

### Local `.env` File

```env
# Carbon Voice OAuth
CARBONVOICE_CLIENT_ID=hIDfX6hmcw5P6IxEG2weC77L
CARBONVOICE_CLIENT_SECRET=ZWAG3sPI9K2SAYzs6pvisMqIoFDoRnq1NUtzv1VgqvLxRzjpIfHpwkMZav6fNOHU
CARBONVOICE_REDIRECT_URI=http://localhost:8000/api/connectors/carbonvoice/oauth/callback
CARBONVOICE_ENVIRONMENT=sandbox

# Carbon Voice Queue
CARBONVOICE_PROCESSING_QUEUE=carbonvoice-processing
```

### Database Model Update

Update `database/models/connector.py`:

```python
class ConnectorType(str, Enum):
    QUICKBOOKS = "quickbooks"
    CARBONVOICE = "carbonvoice"  # Add this
```

---

## Backend Implementation

### 1. Carbon Voice Client (`services/connectors/carbonvoice/client.py`)

```python
"""
Carbon Voice Connector Client.
Handles OAuth2 authentication, token management, and API calls.
"""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urlencode
import base64

from config.settings import (
    CARBONVOICE_CLIENT_ID,
    CARBONVOICE_CLIENT_SECRET,
    CARBONVOICE_REDIRECT_URI,
    CARBONVOICE_ENVIRONMENT,
)
from database.models.connector import ConnectorConfig, ConnectorStatus
from utils.logger import get_logger

logger = get_logger(__name__)

# Carbon Voice API URLs (Confirmed)
CV_OAUTH_AUTHORIZE_URL = "https://api.carbonvoice.app/oauth/authorize"
CV_TOKEN_URL = "https://api.carbonvoice.app/oauth/token"
CV_USERINFO_URL = "https://api.carbonvoice.app/oauth/userinfo"
CV_API_BASE_URL = "https://api.carbonvoice.app"

# OAuth Scopes - To be confirmed during OAuth flow testing
# Carbon Voice uses standard OAuth2 scopes
CV_SCOPES = [
    "openid",
    "profile",
    # Additional scopes may be required based on API access needs
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


# Supported Carbon Voice entities (with correct API endpoints)
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
        api_endpoint="/v3/messages/{channel_id}/by-id",
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
    CarbonVoiceEntityDefinition(
        entity_key="carbonlink",
        api_endpoint="/carbonlink/create",
        display_name="CarbonLinks",
        description="Links to start conversations",
        default_enabled=False,
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
        self.config = config
        self.client_id = CARBONVOICE_CLIENT_ID
        self.client_secret = CARBONVOICE_CLIENT_SECRET
        self.redirect_uri = CARBONVOICE_REDIRECT_URI
        self.environment = CARBONVOICE_ENVIRONMENT
        self.api_base_url = CV_API_BASE_URL

    def is_configured(self) -> bool:
        """Check if Carbon Voice credentials are configured"""
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    # =========================================================================
    # OAuth Methods
    # =========================================================================

    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth2 authorization URL"""
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
        """Exchange authorization code for access and refresh tokens"""
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
        """Refresh the access token using refresh token"""
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

    async def get_user_info(self) -> Dict[str, Any]:
        """Get current user info from Carbon Voice"""
        return await self._make_api_request("/whoami")

    # =========================================================================
    # API Methods
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
    ) -> Dict[str, Any]:
        """Make an authenticated API request to Carbon Voice"""
        url = f"{self.api_base_url}{endpoint}"
        headers = self._get_auth_headers()

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, params=params, json=json_data)
            else:
                response = await client.request(method, url, headers=headers, params=params, json=json_data)

            if response.status_code == 401:
                logger.warning("[CarbonVoice] Access token expired or invalid")
                raise ValueError("Access token expired")

            if response.status_code != 200:
                logger.error(f"[CarbonVoice] API request failed: {response.status_code} - {response.text}")
                raise ValueError(f"API request failed: {response.text}")

            return response.json()

    # =========================================================================
    # Entity-specific methods
    # =========================================================================

    async def get_workspaces(self) -> List[Dict[str, Any]]:
        """Fetch all workspaces for the authenticated user"""
        data = await self._make_api_request("/v5/workspaces")
        return data.get("workspaces", data) if isinstance(data, dict) else data

    async def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Fetch a specific workspace by ID"""
        return await self._make_api_request(f"/v5/workspaces/{workspace_id}")

    async def get_channels(self, workspace_guid: str) -> List[Dict[str, Any]]:
        """Fetch channels (conversations) for a workspace"""
        data = await self._make_api_request(f"/channels/{workspace_guid}")
        return data.get("channels", data) if isinstance(data, dict) else data

    async def get_channel(self, channel_guid: str) -> Dict[str, Any]:
        """Fetch a specific channel by ID"""
        return await self._make_api_request(f"/v2/channel/{channel_guid}")

    async def get_messages(self, channel_id: str, start: int = 0, stop: int = 100) -> List[Dict[str, Any]]:
        """Fetch messages for a channel using sequence numbers"""
        data = await self._make_api_request(f"/v3/messages/{channel_id}/sequential/{start}/{stop}")
        return data.get("messages", data) if isinstance(data, dict) else data

    async def get_messages_by_ids(self, message_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch messages by their IDs (batch request)"""
        data = await self._make_api_request(
            "/v5/messages/by-ids",
            method="POST",
            json_data={"message_ids": message_ids}
        )
        return data.get("messages", data) if isinstance(data, dict) else data

    async def get_recent_messages(self, channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent messages for a channel"""
        data = await self._make_api_request(
            "/v3/messages/recent",
            method="POST",
            json_data={"channel_id": channel_id, "limit": limit}
        )
        return data.get("messages", data) if isinstance(data, dict) else data

    async def get_action_items(self, container_type: str, container_id: str) -> List[Dict[str, Any]]:
        """Fetch action items for a container (workspace/channel)"""
        data = await self._make_api_request(f"/action-items/{container_type}/{container_id}")
        return data.get("action_items", data) if isinstance(data, dict) else data

    async def get_channel_summary(self, channel_id: str) -> Dict[str, Any]:
        """Get AI-generated summary of a conversation"""
        return await self._make_api_request(f"/channels/{channel_id}/summary")

    async def search_messages(self, query: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search messages across workspaces or within a specific workspace"""
        payload = {"query": query}
        if workspace_id:
            payload["workspace_id"] = workspace_id
        data = await self._make_api_request("/v3/search", method="POST", json_data=payload)
        return data.get("results", data) if isinstance(data, dict) else data
```

### 2. API Routes Structure

The routes file will follow the same pattern as `quickbooks_routes.py` with endpoints for:

- Connector CRUD operations
- OAuth flow (start, callback)
- Entity discovery
- Sync operations
- Ingestion operations
- WebSocket for real-time progress

### 3. Sync Service

The sync service will:
1. Fetch workspaces from Carbon Voice
2. For each workspace, fetch conversations
3. For each conversation, fetch discussions
4. Store all data as `ConnectorRawData` records
5. Track progress in `ConnectorSyncLog`

### 4. Ingestion Service

The ingestion service will:
1. Process raw Carbon Voice data
2. Convert discussions/conversations into meaningful chunks
3. Map to appropriate BDE pillars
4. Store as `ConnectorChunk` records

---

## Frontend Implementation

### Carbon Voice API Client (`frontend/src/api/carbonvoiceApi.ts`)

```typescript
import { api } from '../utils/api';

export interface CarbonVoiceConnector {
  id: string;
  tenant_id: string;
  company_id: string;
  connector_type: 'carbonvoice';
  connector_status: 'connected' | 'disconnected' | 'expired' | 'error';
  external_company_id: string | null;
  external_company_name: string | null;
  // ... other fields
}

export const carbonvoiceApi = {
  getInfo: async () => {
    return api.get('/api/connectors/carbonvoice/info');
  },

  list: async (companyId: string) => {
    return api.get('/api/connectors/carbonvoice/', { params: { company_id: companyId } });
  },

  startOAuth: async (companyId: string) => {
    return api.post('/api/connectors/carbonvoice/oauth/start', null, {
      params: { company_id: companyId },
    });
  },

  // ... other methods following QuickBooks pattern
};
```

---

## Testing Strategy

### Unit Tests

1. **Client Tests**
   - OAuth URL generation
   - Token exchange mocking
   - API request formatting

2. **Service Tests**
   - Sync service data transformation
   - Ingestion service chunking logic

### Integration Tests

1. **OAuth Flow**
   - Start OAuth → Callback → Token storage
   - Token refresh mechanism

2. **Sync Flow**
   - API calls to Carbon Voice
   - Data storage in database

3. **End-to-End**
   - Full flow from OAuth to ingested chunks

---

## Deployment Checklist

### Before Deployment

- [ ] All environment variables configured in Azure App Settings
- [ ] Database migrations applied (if any)
- [ ] Azure Queue created for Carbon Voice processing
- [ ] Webhook URL configured in Carbon Voice dashboard (production URL)
- [ ] OAuth callback URL updated in Carbon Voice dashboard (production URL)

### Environment Variables for Production

```
CARBONVOICE_CLIENT_ID=<production_client_id>
CARBONVOICE_CLIENT_SECRET=<production_client_secret>
CARBONVOICE_REDIRECT_URI=https://bde-webapp.azurewebsites.net/api/connectors/carbonvoice/oauth/callback
CARBONVOICE_ENVIRONMENT=production
CARBONVOICE_PROCESSING_QUEUE=carbonvoice-processing
```

### Post-Deployment Verification

- [ ] OAuth flow works end-to-end
- [ ] Data sync fetches data correctly
- [ ] Ingestion processes data into chunks
- [ ] WebSocket progress updates work
- [ ] Webhooks received from Carbon Voice (if applicable)

---

## Data Sync Strategy

### Hierarchical Data Fetching

Carbon Voice data is organized hierarchically:

```
User Account
└── Workspaces (multiple)
    └── Channels (multiple per workspace)
        └── Messages (multiple per channel)
            └── Action Items (optional)
```

### Sync Process

1. **Get User Info**: Call `/whoami` to verify connection and get user details
2. **Fetch Workspaces**: Call `/v5/workspaces` to get all accessible workspaces
3. **For Each Workspace**:
   - Fetch channels: `/channels/{workspace_guid}`
   - Fetch action items: `/action-items/workspace/{workspace_id}`
4. **For Each Channel**:
   - Fetch messages: `/v3/messages/{channel_id}/sequential/{start}/{stop}`
   - Get AI summary: `/channels/{channel_id}/summary` (optional)
5. **Store Raw Data**: Save all fetched data as `ConnectorRawData` records

### Pagination Handling

- Messages use sequence numbers for pagination
- Use `start` and `stop` parameters to paginate through messages
- Batch size recommendation: 100-500 messages per request

### Delta Sync Support

For incremental syncs:
- Track `last_sync_at` timestamp
- Use `/v3/messages/notified` endpoint with date filters
- Only fetch messages updated since last sync

---

## Error Handling

### Common Error Responses

```json
{
  "success": false,
  "requestId": "uuid",
  "errmsg": "error message"
}
```

### Rate Limiting

When rate limited (HTTP 429):
- Check `X-RateLimit-Limit` header
- Check `X-RateLimit-Remaining` header
- Wait until `X-RateLimit-Reset` timestamp

### Token Expiration

- Monitor `token_expiry` in `ConnectorConfig`
- Implement 5-minute buffer for token refresh (like QuickBooks)
- Handle 401 responses by attempting token refresh

---

## Security Considerations

1. **Token Storage**: Store access/refresh tokens securely in database
2. **Webhook Verification**: Use `X-Webhook-Secret` header for webhook authentication
3. **HTTPS Only**: All API calls use HTTPS
4. **State Parameter**: Use random state for OAuth CSRF protection
5. **Scope Limitation**: Request only necessary OAuth scopes

---

## Next Steps

1. **Start Phase 1 Implementation**
   - Add environment variables to `config/settings.py`
   - Update `ConnectorType` enum in database models
   - Create directory structure

2. **Implement Core Client (Phase 2)**
   - Create `CarbonVoiceConnector` class
   - Test OAuth flow with sandbox credentials
   - Verify API access

3. **Build API Routes (Phase 3)**
   - Follow QuickBooks pattern
   - Test each endpoint

4. **Implement Sync & Ingestion (Phase 4)**
   - Hierarchical data fetching
   - Chunk creation for BDE pillars

---

## References

- [Carbon Voice Developer Portal](https://developer.carbonvoice.app)
- [Carbon Voice API Docs](https://api.carbonvoice.app/docs)
- [QuickBooks Implementation Reference](../services/connectors/quickbooks/)
- [BDE Connector Schemas](../api/connector/schemas.py)

---

## Appendix: API Response Examples

### Workspace Response (v5)
```json
{
  "workspace_guid": "string",
  "workspace_name": "string",
  "workspace_description": "string",
  "image_url": "string",
  "owner_guid": "string",
  "type_cd": "string",
  "plan_type": "string",
  "channels": [...],
  "collaborators": [...]
}
```

### Channel Response
```json
{
  "channel_guid": "string",
  "channel_name": "string",
  "channel_kind": "standard",
  "channel_description": "string",
  "workspace_guid": "string",
  "is_private": "string",
  "total_messages": 0,
  "json_collaborators": [...]
}
```

### Message Response (v5)
```json
{
  "message_id": "string",
  "channel_id": "string",
  "creator_id": "string",
  "created_at": "2026-02-03T09:46:10.492Z",
  "transcript": "string",
  "audio_info": {...},
  "attachments": [...],
  "reactions": [...]
}
```
