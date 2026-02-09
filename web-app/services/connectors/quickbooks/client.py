"""
QuickBooks Online Connector Client.
Handles OAuth2 authentication, token management, and API calls.
"""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urlencode, quote
import base64

from config.settings import (
    QUICKBOOKS_CLIENT_ID,
    QUICKBOOKS_CLIENT_SECRET,
    QUICKBOOKS_REDIRECT_URI,
    QUICKBOOKS_ENVIRONMENT,
)
from database.models.connector import ConnectorConfig, ConnectorStatus
from utils.logger import get_logger

logger = get_logger(__name__)


# QuickBooks API URLs
QB_OAUTH_BASE_URL = "https://appcenter.intuit.com/connect/oauth2"
QB_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QB_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"

# API Base URLs by environment
QB_API_BASE_URLS = {
    "sandbox": "https://sandbox-quickbooks.api.intuit.com",
    "production": "https://quickbooks.api.intuit.com",
}

# Scopes required for QuickBooks access
QB_SCOPES = [
    "com.intuit.quickbooks.accounting",  # Full accounting access
    "openid",  # OpenID Connect
    "profile",  # User profile
    "email",  # User email
]


@dataclass
class QuickBooksEntityDefinition:
    """Definition of a QuickBooks entity that can be synced"""
    entity_key: str  # Internal key (e.g., "invoice")
    qb_entity_name: str  # QuickBooks API entity name (e.g., "Invoice")
    display_name: str
    description: str
    is_report: bool
    default_enabled: bool
    pillar_hint: str  # Suggested BDE pillar


# All supported QuickBooks entities
QUICKBOOKS_ENTITIES: List[QuickBooksEntityDefinition] = [
    # Transactional entities
    QuickBooksEntityDefinition(
        entity_key="invoice",
        qb_entity_name="Invoice",
        display_name="Invoices",
        description="Sales invoices sent to customers",
        is_report=False,
        default_enabled=True,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="customer",
        qb_entity_name="Customer",
        display_name="Customers",
        description="Customer records and contact information",
        is_report=False,
        default_enabled=True,
        pillar_hint="customer_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="vendor",
        qb_entity_name="Vendor",
        display_name="Vendors",
        description="Vendor/supplier records",
        is_report=False,
        default_enabled=False,
        pillar_hint="ecosystem_dependency",
    ),
    QuickBooksEntityDefinition(
        entity_key="bill",
        qb_entity_name="Bill",
        display_name="Bills",
        description="Bills/expenses from vendors",
        is_report=False,
        default_enabled=False,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="payment",
        qb_entity_name="Payment",
        display_name="Payments Received",
        description="Customer payments received",
        is_report=False,
        default_enabled=False,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="item",
        qb_entity_name="Item",
        display_name="Products & Services",
        description="Products and services catalog",
        is_report=False,
        default_enabled=False,
        pillar_hint="service_software_ratio",
    ),
    QuickBooksEntityDefinition(
        entity_key="account",
        qb_entity_name="Account",
        display_name="Chart of Accounts",
        description="Account structure and balances",
        is_report=False,
        default_enabled=False,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="employee",
        qb_entity_name="Employee",
        display_name="Employees",
        description="Employee records",
        is_report=False,
        default_enabled=False,
        pillar_hint="operational_maturity",
    ),
    # Reports
    QuickBooksEntityDefinition(
        entity_key="profit_loss",
        qb_entity_name="ProfitAndLoss",
        display_name="Profit & Loss Report",
        description="Income statement showing revenue, expenses, and net income",
        is_report=True,
        default_enabled=True,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="balance_sheet",
        qb_entity_name="BalanceSheet",
        display_name="Balance Sheet",
        description="Assets, liabilities, and equity snapshot",
        is_report=True,
        default_enabled=True,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="cash_flow",
        qb_entity_name="CashFlow",
        display_name="Cash Flow Statement",
        description="Cash inflows and outflows",
        is_report=True,
        default_enabled=False,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="ar_aging",
        qb_entity_name="AgedReceivables",
        display_name="AR Aging Summary",
        description="Accounts receivable aging breakdown",
        is_report=True,
        default_enabled=True,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="ap_aging",
        qb_entity_name="AgedPayables",
        display_name="AP Aging Summary",
        description="Accounts payable aging breakdown",
        is_report=True,
        default_enabled=False,
        pillar_hint="financial_health",
    ),
    QuickBooksEntityDefinition(
        entity_key="customer_income",
        qb_entity_name="CustomerIncome",
        display_name="Income by Customer",
        description="Revenue breakdown by customer",
        is_report=True,
        default_enabled=True,
        pillar_hint="customer_health",
    ),
]

# Quick lookup by entity key
QUICKBOOKS_ENTITY_MAP: Dict[str, QuickBooksEntityDefinition] = {
    e.entity_key: e for e in QUICKBOOKS_ENTITIES
}


class QuickBooksConnector:
    """
    QuickBooks Online connector for OAuth and API operations.
    """

    def __init__(self, config: Optional[ConnectorConfig] = None):
        """
        Initialize QuickBooks connector.

        Args:
            config: Optional ConnectorConfig record. If provided, uses stored tokens.
        """
        self.config = config
        self.client_id = QUICKBOOKS_CLIENT_ID
        self.client_secret = QUICKBOOKS_CLIENT_SECRET
        self.redirect_uri = QUICKBOOKS_REDIRECT_URI
        self.environment = QUICKBOOKS_ENVIRONMENT
        self.api_base_url = QB_API_BASE_URLS.get(self.environment, QB_API_BASE_URLS["sandbox"])

    def is_configured(self) -> bool:
        """Check if QuickBooks credentials are configured"""
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    # =========================================================================
    # OAuth Methods
    # =========================================================================

    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth2 authorization URL for user to connect QuickBooks.

        Args:
            state: Random state string for CSRF protection (store in session)

        Returns:
            URL to redirect user to for QuickBooks authorization
        """
        if not self.is_configured():
            raise ValueError("QuickBooks credentials not configured")

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": " ".join(QB_SCOPES),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        return f"{QB_OAUTH_BASE_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, realm_id: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            realm_id: QuickBooks company ID (realm_id from callback)

        Returns:
            Dict with access_token, refresh_token, expires_in, etc.
        """
        if not self.is_configured():
            raise ValueError("QuickBooks credentials not configured")

        # Prepare Basic auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(QB_TOKEN_URL, headers=headers, data=data)

            if response.status_code != 200:
                logger.error(f"[QuickBooks] Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.text}")

            token_data = response.json()
            token_data["realm_id"] = realm_id

            logger.info(f"[QuickBooks] Successfully exchanged code for tokens, realm_id: {realm_id}")
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

        credentials = f"{self.client_id}:{self.client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(QB_TOKEN_URL, headers=headers, data=data)

            if response.status_code != 200:
                logger.error(f"[QuickBooks] Token refresh failed: {response.text}")
                raise ValueError(f"Token refresh failed: {response.text}")

            token_data = response.json()
            logger.info("[QuickBooks] Successfully refreshed access token")
            return token_data

    async def revoke_token(self) -> bool:
        """
        Revoke the current tokens (disconnect).

        Returns:
            True if successful
        """
        if not self.config or not self.config.refresh_token:
            return True  # Nothing to revoke

        credentials = f"{self.client_id}:{self.client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {"token": self.config.refresh_token}

        async with httpx.AsyncClient() as client:
            response = await client.post(QB_REVOKE_URL, headers=headers, json=payload)

            if response.status_code == 200:
                logger.info("[QuickBooks] Successfully revoked tokens")
                return True
            else:
                logger.warning(f"[QuickBooks] Token revocation returned: {response.status_code}")
                return False

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

    def _get_api_url(self, endpoint: str) -> str:
        """Build full API URL"""
        if not self.config or not self.config.external_company_id:
            raise ValueError("No realm_id (company ID) available")

        realm_id = self.config.external_company_id
        return f"{self.api_base_url}/v3/company/{realm_id}/{endpoint}"

    async def _make_api_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make an authenticated API request to QuickBooks.

        Args:
            endpoint: API endpoint (relative to company URL)
            method: HTTP method
            params: Query parameters

        Returns:
            JSON response data
        """
        url = self._get_api_url(endpoint)
        headers = self._get_auth_headers()

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            else:
                response = await client.request(method, url, headers=headers, params=params)

            if response.status_code == 401:
                logger.warning("[QuickBooks] Access token expired or invalid")
                raise ValueError("Access token expired")

            if response.status_code != 200:
                logger.error(f"[QuickBooks] API request failed: {response.status_code} - {response.text}")
                raise ValueError(f"API request failed: {response.text}")

            return response.json()

    # =========================================================================
    # Company & Entity Discovery
    # =========================================================================

    async def get_company_info(self) -> Dict[str, Any]:
        """
        Get information about the connected QuickBooks company.

        Returns:
            Dict with company name, ID, and other details
        """
        data = await self._make_api_request("companyinfo/" + self.config.external_company_id)
        company_info = data.get("CompanyInfo", {})

        return {
            "company_id": company_info.get("Id"),
            "company_name": company_info.get("CompanyName"),
            "legal_name": company_info.get("LegalName"),
            "country": company_info.get("Country"),
            "fiscal_year_start": company_info.get("FiscalYearStartMonth"),
            "industry_type": company_info.get("NameValue", []),
        }

    async def discover_available_entities(self) -> List[Dict[str, Any]]:
        """
        Discover what entities are available and their record counts.
        This queries QuickBooks to check what data exists.

        Returns:
            List of entity info dicts with counts and availability
        """
        available_entities = []

        for entity_def in QUICKBOOKS_ENTITIES:
            entity_info = {
                "entity_key": entity_def.entity_key,
                "display_name": entity_def.display_name,
                "description": entity_def.description,
                "is_report": entity_def.is_report,
                "default_enabled": entity_def.default_enabled,
                "pillar_hint": entity_def.pillar_hint,
                "record_count": None,
                "is_available": False,
                "error": None,
            }

            try:
                if entity_def.is_report:
                    # For reports, just check if the endpoint responds
                    report_endpoint = f"reports/{entity_def.qb_entity_name}"
                    await self._make_api_request(report_endpoint)
                    entity_info["is_available"] = True
                    entity_info["record_count"] = 1  # Reports are single items
                else:
                    # For entities, get count
                    count = await self._get_entity_count(entity_def.entity_key)
                    entity_info["record_count"] = count
                    entity_info["is_available"] = count > 0

            except Exception as e:
                logger.warning(f"[QuickBooks] Could not check entity {entity_def.entity_key}: {e}")
                entity_info["error"] = str(e)
                entity_info["is_available"] = False

            available_entities.append(entity_info)

        logger.info(f"[QuickBooks] Discovered {len(available_entities)} entities")
        return available_entities

    async def _get_entity_count(self, entity_key: str) -> int:
        """Get count of records for an entity type"""
        entity_def = QUICKBOOKS_ENTITY_MAP.get(entity_key)
        if not entity_def or entity_def.is_report:
            return 0

        query = f"SELECT COUNT(*) FROM {entity_def.qb_entity_name}"
        endpoint = f"query?query={quote(query)}"

        data = await self._make_api_request(endpoint)
        return data.get("QueryResponse", {}).get("totalCount", 0)

    # =========================================================================
    # Data Fetching
    # =========================================================================

    async def fetch_entity_data(
        self,
        entity_key: str,
        start_position: int = 1,
        max_results: int = 1000,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch data for a specific entity type.

        Args:
            entity_key: Entity to fetch (e.g., "invoice", "customer")
            start_position: Pagination start (1-based)
            max_results: Maximum records to fetch per request
            since: For delta syncs, only fetch records modified after this time

        Returns:
            List of raw entity records
        """
        entity_def = QUICKBOOKS_ENTITY_MAP.get(entity_key)
        if not entity_def:
            raise ValueError(f"Unknown entity type: {entity_key}")

        if entity_def.is_report:
            return await self._fetch_report(entity_key)
        else:
            return await self._fetch_transactional_entity(
                entity_key, start_position, max_results, since
            )

    async def _fetch_report(self, entity_key: str) -> List[Dict[str, Any]]:
        """Fetch a report and return it as a single-item list"""
        entity_def = QUICKBOOKS_ENTITY_MAP.get(entity_key)
        if not entity_def or not entity_def.is_report:
            raise ValueError(f"Unknown report: {entity_key}")

        # Add date parameters for reports
        params = {
            "date_macro": "Last Fiscal Year",  # Can be customized
        }

        # Build endpoint using qb_entity_name (e.g., "ProfitAndLoss" -> "reports/ProfitAndLoss")
        endpoint = f"reports/{entity_def.qb_entity_name}"
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
            endpoint = f"{endpoint}?{param_str}"

        data = await self._make_api_request(endpoint)

        # Wrap report in list for consistent handling
        return [{
            "entity_key": entity_key,
            "report_data": data,
            "fetched_at": datetime.utcnow().isoformat(),
        }]

    async def _fetch_transactional_entity(
        self,
        entity_key: str,
        start_position: int,
        max_results: int,
        since: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """Fetch transactional entity data with pagination"""
        entity_def = QUICKBOOKS_ENTITY_MAP.get(entity_key)
        if not entity_def or entity_def.is_report:
            raise ValueError(f"Unknown or non-transactional entity: {entity_key}")

        qb_entity = entity_def.qb_entity_name

        # Build query
        query = f"SELECT * FROM {qb_entity}"

        # Add delta filter if since is provided
        if since:
            # QuickBooks expects ISO 8601 format with timezone
            # Use UTC timezone explicitly
            since_str = since.strftime("%Y-%m-%dT%H:%M:%S-00:00")
            query += f" WHERE MetaData.LastUpdatedTime > '{since_str}'"

        query += f" STARTPOSITION {start_position} MAXRESULTS {max_results}"

        endpoint = f"query?query={quote(query)}"
        data = await self._make_api_request(endpoint)

        # Extract records from response
        query_response = data.get("QueryResponse", {})
        records = query_response.get(qb_entity, [])

        logger.info(f"[QuickBooks] Fetched {len(records)} {entity_key} records")
        return records

    async def fetch_all_entity_data(
        self,
        entity_key: str,
        since: Optional[datetime] = None,
        batch_size: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all data for an entity type with automatic pagination.

        Args:
            entity_key: Entity to fetch
            since: For delta syncs
            batch_size: Records per batch

        Returns:
            All records for the entity
        """
        entity_def = QUICKBOOKS_ENTITY_MAP.get(entity_key)
        if not entity_def:
            raise ValueError(f"Unknown entity type: {entity_key}")

        if entity_def.is_report:
            return await self._fetch_report(entity_key)

        all_records = []
        start_position = 1

        while True:
            records = await self._fetch_transactional_entity(
                entity_key, start_position, batch_size, since
            )

            if not records:
                break

            all_records.extend(records)

            if len(records) < batch_size:
                break  # No more records

            start_position += batch_size

        logger.info(f"[QuickBooks] Fetched total {len(all_records)} {entity_key} records")
        return all_records

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_entity_external_id(self, entity_key: str, record: Dict[str, Any]) -> Optional[str]:
        """Extract the QuickBooks ID from a record"""
        entity_def = QUICKBOOKS_ENTITY_MAP.get(entity_key)
        if entity_def and entity_def.is_report:
            return f"{entity_key}_report"

        return record.get("Id")

    def get_entity_updated_at(self, entity_key: str, record: Dict[str, Any]) -> Optional[datetime]:
        """Extract the last modified timestamp from a record"""
        entity_def = QUICKBOOKS_ENTITY_MAP.get(entity_key)
        if entity_def and entity_def.is_report:
            return datetime.utcnow()

        metadata = record.get("MetaData", {})
        last_updated = metadata.get("LastUpdatedTime")

        if last_updated:
            try:
                return datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            except ValueError:
                pass

        return None

    @staticmethod
    def get_supported_entities() -> List[Dict[str, Any]]:
        """
        Get list of all supported QuickBooks entities.
        This is static - doesn't require a connection.

        Returns:
            List of entity definitions
        """
        return [
            {
                "entity_key": e.entity_key,
                "qb_entity_name": e.qb_entity_name,
                "display_name": e.display_name,
                "description": e.description,
                "is_report": e.is_report,
                "default_enabled": e.default_enabled,
                "pillar_hint": e.pillar_hint,
            }
            for e in QUICKBOOKS_ENTITIES
        ]
