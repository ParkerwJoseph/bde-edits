"""
Database seeding script for roles and permissions.
Run this after database tables are created.
"""
from sqlmodel import Session, select
from database.connection import engine
from database.models import Role, RoleName, RoleLevel, Permission, RolePermission, PromptTemplate, DEFAULT_RAG_PROMPT
from core.permissions import Permissions, PERMISSION_DEFINITIONS


# Define roles (using .value to store as strings in DB)
ROLES = [
    {
        "name": RoleName.SUPER_ADMIN.value,
        "level": RoleLevel.PLATFORM.value,
        "description": "BCP Super Administrator - Full system access",
    },
    {
        "name": RoleName.BCP_ANALYST.value,
        "level": RoleLevel.PLATFORM.value,
        "description": "BCP Analyst - Read-only cross-tenant analytics",
    },
    {
        "name": RoleName.TENANT_ADMIN.value,
        "level": RoleLevel.TENANT.value,
        "description": "Company Administrator - Manage own company",
    },
    {
        "name": RoleName.TENANT_USER.value,
        "level": RoleLevel.TENANT.value,
        "description": "Company User - Basic access within company",
    },
]

# Define which permissions each role has
ROLE_PERMISSIONS = {
    RoleName.SUPER_ADMIN: [
        # All permissions
        Permissions.TENANTS_CREATE,
        Permissions.TENANTS_READ,
        Permissions.TENANTS_READ_ALL,
        Permissions.TENANTS_UPDATE,
        Permissions.TENANTS_DELETE,
        Permissions.TENANTS_ONBOARD,
        Permissions.USERS_READ,
        Permissions.USERS_READ_ALL,
        Permissions.USERS_READ_TENANT,
        Permissions.USERS_CREATE,
        Permissions.USERS_UPDATE,
        Permissions.USERS_UPDATE_ROLE,
        Permissions.USERS_DELETE,
        Permissions.REPORTS_READ,
        Permissions.REPORTS_READ_ALL,
        Permissions.REPORTS_EXPORT,
        Permissions.FILES_UPLOAD,
        Permissions.FILES_READ,
        Permissions.FILES_DELETE,
        Permissions.SETTINGS_READ,
        Permissions.SETTINGS_UPDATE,
        Permissions.SETTINGS_SYSTEM,
    ],
    RoleName.BCP_ANALYST: [
        # Read-only cross-tenant access - NO role updates, NO tenant onboarding, NO tenant creation
        Permissions.TENANTS_READ,
        Permissions.TENANTS_READ_ALL,
        Permissions.USERS_READ,
        Permissions.USERS_READ_ALL,
        Permissions.USERS_READ_TENANT,
        Permissions.REPORTS_READ,
        Permissions.REPORTS_READ_ALL,
        Permissions.REPORTS_EXPORT,
        Permissions.FILES_READ,
        Permissions.FILES_UPLOAD,
        Permissions.SETTINGS_READ,
        Permissions.SETTINGS_UPDATE,
    ],
    RoleName.TENANT_ADMIN: [
        # Own tenant management
        Permissions.TENANTS_READ,
        Permissions.USERS_READ,
        Permissions.USERS_READ_TENANT,
        Permissions.USERS_UPDATE,
        Permissions.USERS_UPDATE_ROLE,
        Permissions.REPORTS_READ,
        Permissions.REPORTS_EXPORT,
        Permissions.FILES_UPLOAD,
        Permissions.FILES_READ,
        Permissions.FILES_DELETE,
        Permissions.SETTINGS_READ,
        Permissions.SETTINGS_UPDATE,
    ],
    RoleName.TENANT_USER: [
        # Basic user access - NO tenant read, NO user read
        Permissions.REPORTS_READ,
        Permissions.REPORTS_EXPORT,
        Permissions.FILES_UPLOAD,
        Permissions.FILES_READ,
        Permissions.FILES_DELETE,
        Permissions.SETTINGS_READ,
        Permissions.SETTINGS_UPDATE,
    ],
}


def seed_database():
    """Seed roles and permissions into the database."""
    with Session(engine) as session:
        # Seed permissions
        permission_map = {}
        for perm_data in PERMISSION_DEFINITIONS:
            existing = session.exec(
                select(Permission).where(Permission.name == perm_data["name"])
            ).first()

            if existing:
                permission_map[perm_data["name"]] = existing
            else:
                permission = Permission(**perm_data)
                session.add(permission)
                session.flush()
                permission_map[perm_data["name"]] = permission

        # Seed roles
        role_map = {}
        for role_data in ROLES:
            existing = session.exec(
                select(Role).where(Role.name == role_data["name"])
            ).first()

            if existing:
                role_map[role_data["name"]] = existing
            else:
                role = Role(**role_data)
                session.add(role)
                session.flush()
                role_map[role_data["name"]] = role

        # Seed role-permission associations
        for role_name, permissions in ROLE_PERMISSIONS.items():
            role_name_str = role_name.value if hasattr(role_name, 'value') else role_name
            role = role_map[role_name_str]
            for perm in permissions:
                perm_name = perm.value if hasattr(perm, 'value') else perm
                permission = permission_map[perm_name]

                # Check if association exists
                existing = session.exec(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission.id
                    )
                ).first()

                if not existing:
                    role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                    session.add(role_perm)

        # Seed default RAG prompt template
        existing_prompt = session.exec(
            select(PromptTemplate).where(PromptTemplate.is_active == True)
        ).first()

        if not existing_prompt:
            prompt = PromptTemplate(
                name="RAG System Prompt",
                description="Main prompt for generating answers based on retrieved document chunks",
                template=DEFAULT_RAG_PROMPT,
                is_active=True,
                version=1
            )
            session.add(prompt)
            print("Default RAG prompt template created.")

        session.commit()
        print("Database seeded successfully!")


def get_role_by_name(session: Session, role_name: RoleName | str) -> Role:
    """Get a role by its name."""
    role_name_str = role_name.value if hasattr(role_name, 'value') else role_name
    return session.exec(select(Role).where(Role.name == role_name_str)).first()


def get_permissions_for_role(session: Session, role_id: str) -> list[str]:
    """Get all permission names for a role."""
    results = session.exec(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    ).all()
    return list(results)


if __name__ == "__main__":
    seed_database()
