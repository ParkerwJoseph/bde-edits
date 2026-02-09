from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from database.models import User, Tenant, Role, Permission, RolePermission
from database.connection import get_session
from az_auth.token import decode_token
from az_auth.service import get_user_by_azure_id
from core.permissions import Permissions


security = HTTPBearer(auto_error=False)


def get_token_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract token from Authorization header or cookie."""
    if credentials:
        return credentials.credentials

    token = request.cookies.get("access_token")
    if token:
        return token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(get_token_from_request),
    session: Session = Depends(get_session),
) -> User:
    """Get current authenticated user from token."""
    payload = decode_token(token)
    azure_oid = payload.get("oid") or payload.get("sub")
    azure_tid = payload.get("tid")

    if not azure_oid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = get_user_by_azure_id(session, azure_oid, azure_tid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def get_user_with_details(
    token: str = Depends(get_token_from_request),
    session: Session = Depends(get_session),
) -> dict:
    """Get current user with tenant and role details."""
    payload = decode_token(token)
    azure_oid = payload.get("oid") or payload.get("sub")
    azure_tid = payload.get("tid")

    if not azure_oid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = get_user_by_azure_id(session, azure_oid, azure_tid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Get tenant
    tenant = session.get(Tenant, user.tenant_id) if user.tenant_id else None

    # Get role
    role = session.get(Role, user.role_id) if user.role_id else None

    # Get permissions
    permissions = []
    if role:
        results = session.exec(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        ).all()
        permissions = list(results)

    return {
        "user": user,
        "tenant": tenant,
        "role": role,
        "permissions": permissions,
    }


def get_user_permissions(session: Session, user: User) -> list[str]:
    """Get all permissions for a user."""
    if not user.role_id:
        return []

    results = session.exec(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == user.role_id)
    ).all()
    return list(results)


class PermissionChecker:
    """Dependency class for checking user permissions."""

    def __init__(self, required_permission: Permissions | str):
        # Support both Permissions enum and string
        self.required_permission = (
            required_permission.value
            if isinstance(required_permission, Permissions)
            else required_permission
        )

    def __call__(
        self,
        user: User = Depends(get_current_user),
        session: Session = Depends(get_session),
    ) -> User:
        permissions = get_user_permissions(session, user)

        if self.required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.required_permission} required",
            )

        return user


def require_permission(permission: Permissions | str):
    """Factory function to create permission dependency."""
    return PermissionChecker(permission)


class TenantAccessChecker:
    """Dependency class for checking tenant access."""

    def __init__(self, allow_cross_tenant: bool = False):
        self.allow_cross_tenant = allow_cross_tenant

    def __call__(
        self,
        tenant_id: str,
        user: User = Depends(get_current_user),
        session: Session = Depends(get_session),
    ) -> User:
        # Get user's tenant
        user_tenant = session.get(Tenant, user.tenant_id) if user.tenant_id else None

        # Platform users with cross-tenant permissions
        if user_tenant and user_tenant.is_platform_tenant:
            permissions = get_user_permissions(session, user)
            # Check if user has cross-tenant read permission
            if Permissions.TENANTS_READ_ALL.value in permissions or Permissions.USERS_READ_ALL.value in permissions:
                return user

        # Same tenant access
        if user.tenant_id == tenant_id:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access resources in another tenant",
        )


def require_tenant_access(allow_cross_tenant: bool = False):
    """Factory function to create tenant access dependency."""
    return TenantAccessChecker(allow_cross_tenant)
