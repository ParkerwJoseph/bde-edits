import msal
from fastapi import HTTPException, status
from urllib.parse import urlencode

from az_auth.config import AzureADConfig, get_azure_config


class AzureADClient:
    """MSAL client wrapper for Azure AD authentication."""

    def __init__(self, config: AzureADConfig | None = None):
        self.config = config or get_azure_config()
        self._app: msal.ConfidentialClientApplication | None = None
        self._multi_tenant_app: msal.ConfidentialClientApplication | None = None

    @property
    def app(self) -> msal.ConfidentialClientApplication:
        """Single-tenant app for BCP staff."""
        if self._app is None:
            self._app = msal.ConfidentialClientApplication(
                self.config.client_id,
                authority=self.config.authority,
                client_credential=self.config.client_secret,
            )
        return self._app

    @property
    def multi_tenant_app(self) -> msal.ConfidentialClientApplication:
        """Multi-tenant app for portfolio company users."""
        if self._multi_tenant_app is None:
            self._multi_tenant_app = msal.ConfidentialClientApplication(
                self.config.client_id,
                authority=self.config.multi_tenant_authority,
                client_credential=self.config.client_secret,
            )
        return self._multi_tenant_app

    def get_auth_url(self, multi_tenant: bool = True) -> str:
        """Generate authorization URL for login redirect.

        Args:
            multi_tenant: If True, uses /common endpoint for any Azure AD tenant.
                         If False, uses BCP's specific tenant.
        """
        app = self.multi_tenant_app if multi_tenant else self.app
        return app.get_authorization_request_url(
            scopes=self.config.scopes,
            redirect_uri=self.config.redirect_uri,
            prompt="select_account",
        )

    def get_admin_consent_url(self, state: str) -> str:
        """Generate admin consent URL for tenant onboarding.

        This URL redirects IT admins to Microsoft's consent page where they
        can grant permissions for their entire organization.
        """
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.onboarding_redirect_uri,
            "state": state,
            "scope": "https://graph.microsoft.com/.default",
        }
        return f"{self.config.admin_consent_url}?{urlencode(params)}"

    def acquire_token(self, code: str, multi_tenant: bool = True) -> dict:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback.
            multi_tenant: If True, uses multi-tenant app.
        """
        app = self.multi_tenant_app if multi_tenant else self.app
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=self.config.scopes,
            redirect_uri=self.config.redirect_uri,
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {result.get('error_description')}",
            )

        return result

    def acquire_token_for_onboarding(self, code: str) -> dict:
        """Exchange authorization code for tokens during onboarding.

        Uses the onboarding redirect URI.
        """
        result = self.multi_tenant_app.acquire_token_by_authorization_code(
            code,
            scopes=["https://graph.microsoft.com/.default"],
            redirect_uri=self.config.onboarding_redirect_uri,
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Onboarding authentication failed: {result.get('error_description')}",
            )

        return result


# Singleton instance
azure_client = AzureADClient()
