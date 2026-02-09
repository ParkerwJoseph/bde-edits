from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, Response
from sqlmodel import Session, select

from database.connection import get_session
from database.models import User, Tenant, Role
from az_auth.client import azure_client
from az_auth.token import extract_claims
from az_auth.service import create_or_update_user, get_tenant_by_azure_id
from az_auth.dependencies import get_current_user, get_user_with_details
from az_auth.config import PLATFORM_TENANT_ID
from config.auth_settings import FRONTEND_URL
from core.permissions import PERMISSION_DEFINITIONS


router = APIRouter()


@router.get("/login")
async def login():
    """Redirect to Azure AD login page (multi-tenant)."""
    return RedirectResponse(url=azure_client.get_auth_url(multi_tenant=True))


@router.get("/callback")
async def auth_callback(code: str, session: Session = Depends(get_session)):
    """Handle OAuth callback from Azure AD."""
    try:
        token_result = azure_client.acquire_token(code, multi_tenant=True)
        access_token = token_result.get("access_token")
        id_token = token_result.get("id_token")

        claims = extract_claims(id_token)

        # Check if user's tenant is allowed
        is_platform_user = claims.tenant_id == PLATFORM_TENANT_ID

        if not is_platform_user:
            # Check if company is onboarded
            tenant = get_tenant_by_azure_id(session, claims.tenant_id)
            if not tenant:
                # Redirect with error - company not onboarded
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/login?error=company_not_onboarded",
                    status_code=status.HTTP_302_FOUND,
                )

            if tenant.status != "active":
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/login?error=tenant_inactive",
                    status_code=status.HTTP_302_FOUND,
                )

        # Create or update user
        user = create_or_update_user(session, claims)

        if not user:
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=provisioning_failed",
                status_code=status.HTTP_302_FOUND,
            )

        response = RedirectResponse(url=FRONTEND_URL)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # Set to True in production
            samesite="lax",
            max_age=604800,  # 7 days
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_me(details: dict = Depends(get_user_with_details)):
    """Get current authenticated user with full details."""
    user: User = details["user"]
    tenant: Tenant = details["tenant"]
    role: Role = details["role"]
    permissions: list[str] = details["permissions"]

    return {
        "id": user.id,
        "azure_oid": user.azure_oid,
        "azure_tid": user.azure_tid,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "first_login_at": user.first_login_at.isoformat() if user.first_login_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "tenant": {
            "id": tenant.id,
            "company_name": tenant.company_name,
            "is_platform_tenant": tenant.is_platform_tenant,
        } if tenant else None,
        "role": {
            "id": role.id,
            "name": role.name,
            "level": role.level,
        } if role else None,
        "permissions": permissions,
    }


@router.post("/logout")
async def logout(response: Response):
    """Logout and clear session cookie."""
    response.delete_cookie(key="access_token", samesite="lax")
    return {"message": "Logged out successfully"}


@router.get("/permissions")
async def get_all_permissions():
    """Get all available permissions for frontend."""
    return {
        "permissions": [
            {
                "name": perm["name"],
                "category": perm["category"],
                "description": perm["description"],
            }
            for perm in PERMISSION_DEFINITIONS
        ]
    }


def format_role_label(role_name: str) -> str:
    """Convert role name to display label."""
    return role_name.replace("_", " ").title()


@router.get("/roles")
async def get_all_roles(session: Session = Depends(get_session)):
    """Get all available roles for frontend."""
    roles = session.exec(select(Role)).all()
    return {
        "roles": [
            {
                "name": role.name,
                "level": role.level,
                "label": format_role_label(role.name),
                "description": role.description,
            }
            for role in roles
        ]
    }
