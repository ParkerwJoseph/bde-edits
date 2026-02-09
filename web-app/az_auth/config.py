from dataclasses import dataclass
from config.auth_settings import (
    TENANT_ID,
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    ONBOARDING_REDIRECT_URI,
    PLATFORM_AZURE_TENANT_ID,
)


@dataclass(frozen=True)
class AzureADConfig:
    tenant_id: str  # BCP's tenant ID
    client_id: str
    client_secret: str
    redirect_uri: str
    onboarding_redirect_uri: str
    scopes: list[str]

    @property
    def authority(self) -> str:
        """Single-tenant authority for BCP staff login."""
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    @property
    def multi_tenant_authority(self) -> str:
        """Multi-tenant authority for portfolio company users."""
        return "https://login.microsoftonline.com/common"

    @property
    def admin_consent_url(self) -> str:
        """URL for admin consent flow (tenant onboarding)."""
        return "https://login.microsoftonline.com/common/adminconsent"


def get_azure_config() -> AzureADConfig:
    return AzureADConfig(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        onboarding_redirect_uri=ONBOARDING_REDIRECT_URI,
        scopes=[],
    )


# Export platform tenant ID for easy access
PLATFORM_TENANT_ID = PLATFORM_AZURE_TENANT_ID
