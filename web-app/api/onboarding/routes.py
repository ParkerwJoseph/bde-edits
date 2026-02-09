from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from database.connection import get_session
from api.tenant import crud as tenant_crud
from api.tenant.schemas import OnboardingValidation
from az_auth.client import azure_client
from az_auth.token import decode_token, extract_claims
from config.auth_settings import FRONTEND_URL

router = APIRouter()


@router.get("/validate/{code}", response_model=OnboardingValidation)
def validate_onboarding_code(
    code: str,
    session: Session = Depends(get_session),
):
    """Validate an onboarding code without starting the flow."""
    is_valid, tenant, error = tenant_crud.validate_onboarding_code(session, code)

    if not is_valid:
        return OnboardingValidation(valid=False, error=error)

    return OnboardingValidation(
        valid=True,
        tenant_id=tenant.id,
        company_name=tenant.company_name,
    )


@router.get("/start/{code}")
def start_onboarding(
    code: str,
    session: Session = Depends(get_session),
):
    """Start the Azure AD admin consent flow.

    This redirects the IT admin to Microsoft's admin consent page.
    """
    is_valid, tenant, error = tenant_crud.validate_onboarding_code(session, code)

    if not is_valid:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{FRONTEND_URL}/onboarding/{code}?error={error}",
            status_code=status.HTTP_302_FOUND,
        )

    # Generate admin consent URL with the onboarding code as state
    consent_url = azure_client.get_admin_consent_url(state=code)

    return RedirectResponse(url=consent_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
def onboarding_callback(
    admin_consent: str = None,
    tenant: str = None,  # Azure tenant ID from consent
    state: str = None,   # Our onboarding code
    error: str = None,
    error_description: str = None,
    session: Session = Depends(get_session),
):
    """Handle Azure AD admin consent callback.

    After the IT admin grants consent, Azure redirects here with:
    - admin_consent: "True" if consent was granted
    - tenant: The Azure tenant ID that granted consent
    - state: Our onboarding code (passed through from start)
    """
    # Handle consent denial
    if error:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/onboarding/{state}?error={error_description or error}",
            status_code=status.HTTP_302_FOUND,
        )

    if admin_consent != "True":
        return RedirectResponse(
            url=f"{FRONTEND_URL}/onboarding/{state}?error=Consent not granted",
            status_code=status.HTTP_302_FOUND,
        )

    if not state or not tenant:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/onboarding/error?error=Invalid callback parameters",
            status_code=status.HTTP_302_FOUND,
        )

    # Validate the onboarding code
    is_valid, bde_tenant, error_msg = tenant_crud.validate_onboarding_code(session, state)

    if not is_valid:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/onboarding/{state}?error={error_msg}",
            status_code=status.HTTP_302_FOUND,
        )

    # Check if this Azure tenant is already linked to another BDE tenant
    existing = tenant_crud.get_tenant_by_azure_id(session, tenant)
    if existing:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/onboarding/{state}?error=This Azure AD is already registered with another tenant",
            status_code=status.HTTP_302_FOUND,
        )

    # Complete the onboarding
    tenant_crud.complete_onboarding(session, bde_tenant, tenant)

    # Redirect to success page
    return RedirectResponse(
        url=f"{FRONTEND_URL}/onboarding/{state}?success=true",
        status_code=status.HTTP_302_FOUND,
    )
