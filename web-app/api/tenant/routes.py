from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from database.connection import get_session
from database.models import Tenant
from api.tenant import crud
from api.tenant.schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
    OnboardingPackage,
)
from config.auth_settings import FRONTEND_URL
from az_auth.dependencies import require_permission
from database.models.user import User
from core.permissions import Permissions

router = APIRouter()


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    data: TenantCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.TENANTS_CREATE)),
):
    """Create a new tenant. (Super Admin only)"""
    tenant = crud.create_tenant(session, data)
    return tenant


@router.get("", response_model=TenantListResponse)
def list_tenants(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.TENANTS_READ_ALL)),
):
    """List all tenants. (Platform users only)"""
    tenants = crud.get_all_tenants(session, skip, limit)
    total = crud.get_tenants_count(session)
    return TenantListResponse(tenants=tenants, total=total)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.TENANTS_READ)),
):
    """Get tenant details."""
    tenant = crud.get_tenant(session, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.TENANTS_UPDATE)),
):
    """Update tenant details. (Super Admin only)"""
    tenant = crud.get_tenant(session, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return crud.update_tenant(session, tenant, data)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.TENANTS_DELETE)),
):
    """Delete a tenant. (Super Admin only)"""
    tenant = crud.get_tenant(session, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant.is_platform_tenant:
        raise HTTPException(status_code=400, detail="Cannot delete platform tenant")

    crud.delete_tenant(session, tenant)


@router.post("/{tenant_id}/onboarding", response_model=OnboardingPackage)
def generate_onboarding(
    tenant_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.TENANTS_ONBOARD)),
):
    """Generate onboarding package for a tenant. (Super Admin only)"""
    tenant = crud.get_tenant(session, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant.is_platform_tenant:
        raise HTTPException(status_code=400, detail="Cannot onboard platform tenant")

    if tenant.azure_tenant_id:
        raise HTTPException(status_code=400, detail="Tenant already has Azure AD linked")

    tenant = crud.generate_onboarding_code(session, tenant)

    onboarding_url = f"{FRONTEND_URL}/onboarding/{tenant.onboarding_code}"

    return OnboardingPackage(
        tenant_id=tenant.id,
        company_name=tenant.company_name,
        onboarding_url=onboarding_url,
        onboarding_code=tenant.onboarding_code,
        expires_at=tenant.onboarding_code_expiry,
    )
