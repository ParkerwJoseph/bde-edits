from datetime import datetime
from sqlmodel import Session, select

from database.models import User, Tenant, TenantStatus, Role, RoleName
from az_auth.token import TokenClaims
from az_auth.config import PLATFORM_TENANT_ID
from database.seed import get_role_by_name


def get_user_by_azure_id(session: Session, azure_oid: str, azure_tid: str = None) -> User | None:
    """Find user by Azure AD Object ID (and optionally tenant ID)."""
    query = select(User).where(User.azure_oid == azure_oid)
    if azure_tid:
        query = query.where(User.azure_tid == azure_tid)
    return session.exec(query).first()


def get_tenant_by_azure_id(session: Session, azure_tenant_id: str) -> Tenant | None:
    """Find tenant by Azure AD tenant ID."""
    return session.exec(
        select(Tenant).where(Tenant.azure_tenant_id == azure_tenant_id)
    ).first()


def is_first_user_in_tenant(session: Session, tenant_id: str) -> bool:
    """Check if this would be the first user in a tenant."""
    existing = session.exec(
        select(User).where(User.tenant_id == tenant_id)
    ).first()
    return existing is None


def get_or_create_platform_tenant(session: Session) -> Tenant:
    """Get or create the platform tenant (BCP)."""
    if not PLATFORM_TENANT_ID:
        raise ValueError("PLATFORM_AZURE_TENANT_ID not configured")

    tenant = get_tenant_by_azure_id(session, PLATFORM_TENANT_ID)
    if tenant:
        return tenant

    tenant = Tenant(
        azure_tenant_id=PLATFORM_TENANT_ID,
        company_name="BCP",
        status=TenantStatus.ACTIVE,
        is_platform_tenant=True,
        consent_timestamp=datetime.utcnow(),
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def provision_user(session: Session, claims: TokenClaims) -> User:
    """Provision a new user or update existing user.

    This implements the auto-provisioning logic:
    - First user from platform tenant -> needs manual role assignment
    - First user from portfolio company -> TENANT_ADMIN
    - Subsequent users -> TENANT_USER
    """
    # Check if user already exists
    existing_user = get_user_by_azure_id(session, claims.azure_id, claims.tenant_id)
    if existing_user:
        # Update last login and any changed profile info
        existing_user.email = claims.email
        existing_user.display_name = claims.name
        existing_user.last_login_at = datetime.utcnow()
        existing_user.updated_at = datetime.utcnow()
        session.add(existing_user)
        session.commit()
        session.refresh(existing_user)
        return existing_user

    # New user - need to resolve tenant and assign role
    is_platform_user = claims.tenant_id == PLATFORM_TENANT_ID

    if is_platform_user:
        # Platform (BCP) user
        tenant = get_or_create_platform_tenant(session)
        # Platform users don't get auto-assigned roles - must be set manually
        # But first platform user could be set as TENANT_USER as default
        role = get_role_by_name(session, RoleName.TENANT_USER)
    else:
        # Portfolio company user
        tenant = get_tenant_by_azure_id(session, claims.tenant_id)

        if not tenant:
            # Company not onboarded
            return None

        if tenant.status != TenantStatus.ACTIVE:
            # Tenant not active
            return None

        # Determine role based on whether first user
        if is_first_user_in_tenant(session, tenant.id):
            role = get_role_by_name(session, RoleName.TENANT_ADMIN)
        else:
            role = get_role_by_name(session, RoleName.TENANT_USER)

    # Create the user
    now = datetime.utcnow()
    user = User(
        azure_oid=claims.azure_id,
        azure_tid=claims.tenant_id,
        tenant_id=tenant.id,
        role_id=role.id if role else None,
        email=claims.email,
        display_name=claims.name,
        is_active=True,
        first_login_at=now,
        last_login_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_or_update_user(session: Session, claims: TokenClaims) -> User:
    """Create new user or update existing user from token claims.

    This is the main entry point for user provisioning during login.
    """
    return provision_user(session, claims)
