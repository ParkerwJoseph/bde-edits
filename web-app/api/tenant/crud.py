import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select

from database.models import Tenant, TenantStatus
from api.tenant.schemas import TenantCreate, TenantUpdate


def create_tenant(session: Session, data: TenantCreate) -> Tenant:
    """Create a new tenant."""
    tenant = Tenant(
        company_name=data.company_name,
        status=TenantStatus.PENDING,
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def get_tenant(session: Session, tenant_id: str) -> Optional[Tenant]:
    """Get tenant by ID."""
    return session.get(Tenant, tenant_id)


def get_tenant_by_azure_id(session: Session, azure_tenant_id: str) -> Optional[Tenant]:
    """Get tenant by Azure tenant ID."""
    return session.exec(
        select(Tenant).where(Tenant.azure_tenant_id == azure_tenant_id)
    ).first()


def get_tenant_by_onboarding_code(session: Session, code: str) -> Optional[Tenant]:
    """Get tenant by onboarding code."""
    return session.exec(
        select(Tenant).where(Tenant.onboarding_code == code)
    ).first()


def get_all_tenants(session: Session, skip: int = 0, limit: int = 100) -> list[Tenant]:
    """Get all tenants with pagination."""
    return list(session.exec(
        select(Tenant).offset(skip).limit(limit)
    ).all())


def get_tenants_count(session: Session) -> int:
    """Get total count of tenants."""
    return len(session.exec(select(Tenant)).all())


def update_tenant(session: Session, tenant: Tenant, data: TenantUpdate) -> Tenant:
    """Update tenant details."""
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tenant, key, value)
    tenant.updated_at = datetime.utcnow()
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def delete_tenant(session: Session, tenant: Tenant) -> None:
    """Delete a tenant."""
    session.delete(tenant)
    session.commit()


def generate_onboarding_code(session: Session, tenant: Tenant, expiry_hours: int = 72) -> Tenant:
    """Generate a new onboarding code for a tenant."""
    tenant.onboarding_code = secrets.token_urlsafe(32)
    tenant.onboarding_code_expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
    tenant.updated_at = datetime.utcnow()
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def validate_onboarding_code(session: Session, code: str) -> tuple[bool, Optional[Tenant], Optional[str]]:
    """Validate an onboarding code.

    Returns:
        Tuple of (is_valid, tenant, error_message)
    """
    tenant = get_tenant_by_onboarding_code(session, code)

    if not tenant:
        return False, None, "Invalid onboarding code"

    if tenant.onboarding_code_expiry and tenant.onboarding_code_expiry < datetime.utcnow():
        return False, tenant, "Onboarding code has expired"

    if tenant.status == TenantStatus.ACTIVE:
        return False, tenant, "Tenant already onboarded"

    if tenant.azure_tenant_id:
        return False, tenant, "Tenant already linked to an Azure AD"

    return True, tenant, None


def complete_onboarding(
    session: Session,
    tenant: Tenant,
    azure_tenant_id: str
) -> Tenant:
    """Complete tenant onboarding after Azure consent."""
    tenant.azure_tenant_id = azure_tenant_id
    tenant.status = TenantStatus.ACTIVE
    tenant.consent_timestamp = datetime.utcnow()
    tenant.onboarding_code = None  # Invalidate the code
    tenant.onboarding_code_expiry = None
    tenant.updated_at = datetime.utcnow()
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def get_or_create_platform_tenant(session: Session, azure_tenant_id: str, company_name: str = "BCP") -> Tenant:
    """Get or create the platform tenant (BCP)."""
    tenant = get_tenant_by_azure_id(session, azure_tenant_id)
    if tenant:
        return tenant

    tenant = Tenant(
        azure_tenant_id=azure_tenant_id,
        company_name=company_name,
        status=TenantStatus.ACTIVE,
        is_platform_tenant=True,
        consent_timestamp=datetime.utcnow(),
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant
