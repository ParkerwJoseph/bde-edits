/**
 * Permission constants for type-safe permission checking.
 * These mirror the backend permissions in core/permissions.py
 * The backend is the source of truth - these provide type safety and autocompletion.
 */

export const Permissions = {
  // Tenant management
  TENANTS_CREATE: 'tenants:create',
  TENANTS_READ: 'tenants:read',
  TENANTS_READ_ALL: 'tenants:read_all',
  TENANTS_UPDATE: 'tenants:update',
  TENANTS_DELETE: 'tenants:delete',
  TENANTS_ONBOARD: 'tenants:onboard',

  // User management
  USERS_READ: 'users:read',
  USERS_READ_ALL: 'users:read_all',
  USERS_READ_TENANT: 'users:read_tenant',
  USERS_CREATE: 'users:create',
  USERS_UPDATE: 'users:update',
  USERS_UPDATE_ROLE: 'users:update_role',
  USERS_DELETE: 'users:delete',

  // Reports & data
  REPORTS_READ: 'reports:read',
  REPORTS_READ_ALL: 'reports:read_all',
  REPORTS_EXPORT: 'reports:export',

  // Files
  FILES_UPLOAD: 'files:upload',
  FILES_READ: 'files:read',
  FILES_DELETE: 'files:delete',

  // Settings
  SETTINGS_READ: 'settings:read',
  SETTINGS_UPDATE: 'settings:update',
  SETTINGS_SYSTEM: 'settings:system',

  // Connectors
  CONNECTORS_READ: 'connectors:read',
  CONNECTORS_MANAGE: 'connectors:manage',
} as const;

export type Permission = (typeof Permissions)[keyof typeof Permissions];

/**
 * Role name constants for type-safe role checking.
 */
export const Roles = {
  SUPER_ADMIN: 'super_admin',
  BCP_ANALYST: 'bcp_analyst',
  TENANT_ADMIN: 'tenant_admin',
  TENANT_USER: 'tenant_user',
} as const;

export type RoleName = (typeof Roles)[keyof typeof Roles];

/**
 * Role level constants.
 */
export const RoleLevels = {
  PLATFORM: 'platform',
  TENANT: 'tenant',
} as const;

export type RoleLevel = (typeof RoleLevels)[keyof typeof RoleLevels];
