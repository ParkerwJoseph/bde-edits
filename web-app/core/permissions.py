"""
Centralized permission definitions.
All permission names should be referenced from here.
"""
from enum import Enum


class Permissions(str, Enum):
    # Tenant management
    TENANTS_CREATE = "tenants:create"
    TENANTS_READ = "tenants:read"
    TENANTS_READ_ALL = "tenants:read_all"
    TENANTS_UPDATE = "tenants:update"
    TENANTS_DELETE = "tenants:delete"
    TENANTS_ONBOARD = "tenants:onboard"

    # User management
    USERS_READ = "users:read"
    USERS_READ_ALL = "users:read_all"
    USERS_READ_TENANT = "users:read_tenant"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_UPDATE_ROLE = "users:update_role"
    USERS_DELETE = "users:delete"

    # Reports & data
    REPORTS_READ = "reports:read"
    REPORTS_READ_ALL = "reports:read_all"
    REPORTS_EXPORT = "reports:export"

    # Files
    FILES_UPLOAD = "files:upload"
    FILES_READ = "files:read"
    FILES_DELETE = "files:delete"

    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"
    SETTINGS_SYSTEM = "settings:system"

    # Scoring
    SCORING_READ = "scoring:read"
    SCORING_WRITE = "scoring:write"
    SCORING_ADMIN = "scoring:admin"

    # Connectors
    CONNECTORS_READ = "connectors:read"
    CONNECTORS_MANAGE = "connectors:manage"


# Permission definitions for database seeding
PERMISSION_DEFINITIONS = [
    # Tenant management
    {"name": Permissions.TENANTS_CREATE.value, "category": "tenants", "description": "Create new tenants"},
    {"name": Permissions.TENANTS_READ.value, "category": "tenants", "description": "View own tenant details"},
    {"name": Permissions.TENANTS_READ_ALL.value, "category": "tenants", "description": "View all tenants"},
    {"name": Permissions.TENANTS_UPDATE.value, "category": "tenants", "description": "Update tenant settings"},
    {"name": Permissions.TENANTS_DELETE.value, "category": "tenants", "description": "Delete tenants"},
    {"name": Permissions.TENANTS_ONBOARD.value, "category": "tenants", "description": "Generate onboarding links"},

    # User management
    {"name": Permissions.USERS_READ.value, "category": "users", "description": "View own user details"},
    {"name": Permissions.USERS_READ_ALL.value, "category": "users", "description": "View all users across tenants"},
    {"name": Permissions.USERS_READ_TENANT.value, "category": "users", "description": "View users in own tenant"},
    {"name": Permissions.USERS_CREATE.value, "category": "users", "description": "Create users"},
    {"name": Permissions.USERS_UPDATE.value, "category": "users", "description": "Update user details"},
    {"name": Permissions.USERS_UPDATE_ROLE.value, "category": "users", "description": "Change user roles"},
    {"name": Permissions.USERS_DELETE.value, "category": "users", "description": "Delete users"},

    # Reports & data
    {"name": Permissions.REPORTS_READ.value, "category": "reports", "description": "View reports"},
    {"name": Permissions.REPORTS_READ_ALL.value, "category": "reports", "description": "View reports across tenants"},
    {"name": Permissions.REPORTS_EXPORT.value, "category": "reports", "description": "Export report data"},

    # Files
    {"name": Permissions.FILES_UPLOAD.value, "category": "files", "description": "Upload files"},
    {"name": Permissions.FILES_READ.value, "category": "files", "description": "View/download files"},
    {"name": Permissions.FILES_DELETE.value, "category": "files", "description": "Delete files"},

    # Settings
    {"name": Permissions.SETTINGS_READ.value, "category": "settings", "description": "View settings"},
    {"name": Permissions.SETTINGS_UPDATE.value, "category": "settings", "description": "Update settings"},
    {"name": Permissions.SETTINGS_SYSTEM.value, "category": "settings", "description": "Manage system settings"},

    # Scoring
    {"name": Permissions.SCORING_READ.value, "category": "scoring", "description": "View BDE scores and analysis"},
    {"name": Permissions.SCORING_WRITE.value, "category": "scoring", "description": "Trigger scoring and analysis"},
    {"name": Permissions.SCORING_ADMIN.value, "category": "scoring", "description": "Manage scoring configuration"},

    # Connectors
    {"name": Permissions.CONNECTORS_READ.value, "category": "connectors", "description": "View connector configurations"},
    {"name": Permissions.CONNECTORS_MANAGE.value, "category": "connectors", "description": "Manage connector integrations"},
]
