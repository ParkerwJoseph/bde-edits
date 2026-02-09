import type { ReactNode } from 'react';
import { usePermission } from '../../hooks/usePermission';
import type { Permission, RoleName } from '../../constants/permissions';

interface PermissionGateProps {
  /** Single permission required (if array, checks if user has ANY) */
  permission?: Permission | string | (Permission | string)[];
  /** Show if user has ANY of these permissions */
  anyOf?: (Permission | string)[];
  /** Show if user has ALL of these permissions */
  allOf?: (Permission | string)[];
  /** Required role(s) - if array, checks if user has ANY */
  role?: RoleName | string | (RoleName | string)[];
  /** What to render when access is denied (default: null) */
  fallback?: ReactNode;
  /** Content to render when access is granted */
  children: ReactNode;
}

/**
 * Declarative component for conditional rendering based on permissions.
 *
 * @example
 * // Single permission
 * <PermissionGate permission={Permissions.TENANTS_CREATE}>
 *   <button>Create Tenant</button>
 * </PermissionGate>
 *
 * @example
 * // Any of multiple permissions
 * <PermissionGate anyOf={[Permissions.USERS_READ_ALL, Permissions.USERS_READ_TENANT]}>
 *   <UserList />
 * </PermissionGate>
 *
 * @example
 * // All permissions required
 * <PermissionGate allOf={[Permissions.TENANTS_READ, Permissions.TENANTS_UPDATE]}>
 *   <EditTenantForm />
 * </PermissionGate>
 *
 * @example
 * // Role-based check
 * <PermissionGate role={Roles.SUPER_ADMIN}>
 *   <AdminPanel />
 * </PermissionGate>
 *
 * @example
 * // With fallback content
 * <PermissionGate permission={Permissions.FILES_UPLOAD} fallback={<p>No access</p>}>
 *   <FileUploader />
 * </PermissionGate>
 */
export function PermissionGate({
  permission,
  anyOf,
  allOf,
  role,
  fallback = null,
  children,
}: PermissionGateProps) {
  const { hasPermission, hasAnyPermission, hasAllPermissions, hasRole } = usePermission();

  // Check single permission
  if (permission !== undefined) {
    if (!hasPermission(permission)) {
      return <>{fallback}</>;
    }
  }

  // Check anyOf permissions
  if (anyOf !== undefined && anyOf.length > 0) {
    if (!hasAnyPermission(anyOf)) {
      return <>{fallback}</>;
    }
  }

  // Check allOf permissions
  if (allOf !== undefined && allOf.length > 0) {
    if (!hasAllPermissions(allOf)) {
      return <>{fallback}</>;
    }
  }

  // Check role
  if (role !== undefined) {
    if (!hasRole(role)) {
      return <>{fallback}</>;
    }
  }

  return <>{children}</>;
}
