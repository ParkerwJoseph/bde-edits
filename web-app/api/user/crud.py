from typing import Optional
from datetime import datetime
from sqlmodel import Session, select

from database.models import User, Role, RoleName, Tenant
from database.seed import get_role_by_name


def get_user(session: Session, user_id: str) -> Optional[User]:
    """Get user by ID."""
    return session.get(User, user_id)


def get_users_by_tenant(session: Session, tenant_id: str, skip: int = 0, limit: int = 100) -> list[User]:
    """Get all users in a tenant."""
    return list(session.exec(
        select(User).where(User.tenant_id == tenant_id).offset(skip).limit(limit)
    ).all())


def get_all_users(session: Session, skip: int = 0, limit: int = 100) -> list[User]:
    """Get all users across all tenants."""
    return list(session.exec(
        select(User).offset(skip).limit(limit)
    ).all())


def count_users_by_tenant(session: Session, tenant_id: str) -> int:
    """Count users in a tenant."""
    return len(session.exec(select(User).where(User.tenant_id == tenant_id)).all())


def count_all_users(session: Session) -> int:
    """Count all users."""
    return len(session.exec(select(User)).all())


def update_user_role(session: Session, user: User, role_name: RoleName) -> User:
    """Update user's role."""
    role = get_role_by_name(session, role_name)
    if not role:
        raise ValueError(f"Role {role_name} not found")

    user.role_id = role.id
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user_status(session: Session, user: User, is_active: bool) -> User:
    """Update user's active status."""
    user.is_active = is_active
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def delete_user(session: Session, user: User) -> None:
    """Delete a user."""
    session.delete(user)
    session.commit()


def get_user_with_details(session: Session, user: User) -> dict:
    """Get user with tenant and role details."""
    tenant = session.get(Tenant, user.tenant_id) if user.tenant_id else None
    role = session.get(Role, user.role_id) if user.role_id else None

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "first_login_at": user.first_login_at,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "tenant_name": tenant.company_name if tenant else None,
        "role_name": role.name if role else None,
    }


def can_modify_user_role(
    session: Session,
    requester: User,
    target: User,
    new_role: RoleName
) -> tuple[bool, str]:
    """Check if requester can modify target user's role.

    Returns:
        Tuple of (can_modify, reason)
    """
    requester_role = session.get(Role, requester.role_id) if requester.role_id else None
    target_role = session.get(Role, target.role_id) if target.role_id else None
    new_role_obj = get_role_by_name(session, new_role)

    if not requester_role:
        return False, "Requester has no role"

    requester_tenant = session.get(Tenant, requester.tenant_id) if requester.tenant_id else None

    # Super Admin can modify anyone
    if requester_role.name == RoleName.SUPER_ADMIN.value:
        return True, ""

    # BCP Analyst cannot modify roles (read-only access)
    if requester_role.name == RoleName.BCP_ANALYST.value:
        return False, "BCP Analyst has read-only access"

    # Tenant Admin can only modify users in their own tenant
    if requester_role.name == RoleName.TENANT_ADMIN.value:
        if requester.tenant_id != target.tenant_id:
            return False, "Cannot modify users in other tenants"

        new_role_value = new_role.value if hasattr(new_role, 'value') else new_role
        if new_role_value == RoleName.TENANT_ADMIN.value:
            return False, "Tenant Admin cannot create other Tenant Admins"

        if new_role_value in [RoleName.SUPER_ADMIN.value, RoleName.BCP_ANALYST.value]:
            return False, "Cannot assign platform-level roles"

        return True, ""

    return False, "Insufficient permissions to modify user roles"
