from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from database.connection import get_session
from database.models import User, Tenant, Role
from api.user import crud
from api.user.schemas import (
    UserResponse,
    UserWithDetails,
    UserListResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from az_auth.dependencies import get_current_user, get_user_permissions
from core.permissions import Permissions

router = APIRouter()


@router.get("", response_model=UserListResponse)
def list_users(
    tenant_id: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List users. Platform admins see all, tenant users see own tenant only."""
    permissions = get_user_permissions(session, current_user)

    # Check if user can view all users
    if Permissions.USERS_READ_ALL.value in permissions:
        if tenant_id:
            users = crud.get_users_by_tenant(session, tenant_id, skip, limit)
            total = crud.count_users_by_tenant(session, tenant_id)
        else:
            users = crud.get_all_users(session, skip, limit)
            total = crud.count_all_users(session)
    elif Permissions.USERS_READ_TENANT.value in permissions:
        # Can only view own tenant
        users = crud.get_users_by_tenant(session, current_user.tenant_id, skip, limit)
        total = crud.count_users_by_tenant(session, current_user.tenant_id)
    else:
        raise HTTPException(status_code=403, detail="No permission to view users")

    # Convert to response with details
    users_with_details = [crud.get_user_with_details(session, u) for u in users]

    return UserListResponse(users=users_with_details, total=total)


@router.get("/{user_id}", response_model=UserWithDetails)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get user details."""
    user = crud.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    permissions = get_user_permissions(session, current_user)

    # Check access
    if Permissions.USERS_READ_ALL.value not in permissions:
        if Permissions.USERS_READ_TENANT.value in permissions:
            if user.tenant_id != current_user.tenant_id:
                raise HTTPException(status_code=403, detail="Cannot view users in other tenants")
        elif Permissions.USERS_READ.value in permissions:
            if user.id != current_user.id:
                raise HTTPException(status_code=403, detail="Can only view own profile")
        else:
            raise HTTPException(status_code=403, detail="No permission to view user")

    return crud.get_user_with_details(session, user)


@router.put("/{user_id}/role", response_model=UserWithDetails)
def update_user_role(
    user_id: str,
    data: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Update user's role."""
    target_user = crud.get_user(session, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    permissions = get_user_permissions(session, current_user)
    if Permissions.USERS_UPDATE_ROLE.value not in permissions:
        raise HTTPException(status_code=403, detail="No permission to update roles")

    # Check if this role change is allowed
    can_modify, reason = crud.can_modify_user_role(session, current_user, target_user, data.role_name)
    if not can_modify:
        raise HTTPException(status_code=403, detail=reason)

    updated_user = crud.update_user_role(session, target_user, data.role_name)
    return crud.get_user_with_details(session, updated_user)


@router.put("/{user_id}/status", response_model=UserWithDetails)
def update_user_status(
    user_id: str,
    data: UserStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Update user's active status (enable/disable account)."""
    target_user = crud.get_user(session, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    permissions = get_user_permissions(session, current_user)
    if Permissions.USERS_UPDATE.value not in permissions:
        raise HTTPException(status_code=403, detail="No permission to update users")

    # Cannot deactivate yourself
    if target_user.id == current_user.id and not data.is_active:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    # Tenant admins can only update users in their tenant
    if Permissions.USERS_READ_ALL.value not in permissions:
        if target_user.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Cannot modify users in other tenants")

    updated_user = crud.update_user_status(session, target_user, data.is_active)
    return crud.get_user_with_details(session, updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Delete a user."""
    target_user = crud.get_user(session, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    permissions = get_user_permissions(session, current_user)
    if Permissions.USERS_DELETE.value not in permissions:
        raise HTTPException(status_code=403, detail="No permission to delete users")

    # Cannot delete yourself
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Tenant admins can only delete users in their tenant
    if Permissions.USERS_READ_ALL.value not in permissions:
        if target_user.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Cannot delete users in other tenants")

    crud.delete_user(session, target_user)
