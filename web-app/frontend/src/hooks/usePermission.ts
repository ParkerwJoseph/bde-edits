import { useCallback, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { usePermissionContext } from '../context/PermissionContext';
import type { Permission, RoleName, RoleLevel } from '../constants/permissions';
import { Roles, RoleLevels } from '../constants/permissions';
import type { RoleInfo } from '../api/permissionApi';

/**
 * Hook for checking user permissions.
 * Provides various methods to check if the current user has specific permissions or roles.
 */
export function usePermission() {
  const { user } = useAuth();
  const userPermissions = user?.permissions ?? [];
  const userRole = user?.role?.name ?? null;

  /**
   * Check if the user has a specific permission.
   * @param permission - Single permission or array of permissions (checks if user has ANY)
   */
  const hasPermission = useCallback(
    (permission: Permission | string | (Permission | string)[]): boolean => {
      if (Array.isArray(permission)) {
        return permission.some((p) => userPermissions.includes(p));
      }
      return userPermissions.includes(permission);
    },
    [userPermissions]
  );

  /**
   * Check if the user has ANY of the specified permissions.
   */
  const hasAnyPermission = useCallback(
    (permissions: (Permission | string)[]): boolean => {
      return permissions.some((p) => userPermissions.includes(p));
    },
    [userPermissions]
  );

  /**
   * Check if the user has ALL of the specified permissions.
   */
  const hasAllPermissions = useCallback(
    (permissions: (Permission | string)[]): boolean => {
      return permissions.every((p) => userPermissions.includes(p));
    },
    [userPermissions]
  );

  /**
   * Check if the user has a specific role.
   * @param role - Single role or array of roles (checks if user has ANY)
   */
  const hasRole = useCallback(
    (role: RoleName | string | (RoleName | string)[]): boolean => {
      if (!userRole) return false;
      if (Array.isArray(role)) {
        return role.includes(userRole);
      }
      return userRole === role;
    },
    [userRole]
  );

  /**
   * Check if user is at a specific role level (platform or tenant).
   */
  const hasRoleLevel = useCallback(
    (level: RoleLevel | string): boolean => {
      return user?.role?.level === level;
    },
    [user?.role?.level]
  );

  /**
   * Check if user is a platform-level user.
   */
  const isPlatformUser = useMemo(
    () => user?.role?.level === RoleLevels.PLATFORM,
    [user?.role?.level]
  );

  /**
   * Check if user is a tenant-level user.
   */
  const isTenantUser = useMemo(
    () => user?.role?.level === RoleLevels.TENANT,
    [user?.role?.level]
  );

  /**
   * Check if user is a super admin.
   */
  const isSuperAdmin = useMemo(() => userRole === Roles.SUPER_ADMIN, [userRole]);

  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    hasRoleLevel,
    isPlatformUser,
    isTenantUser,
    isSuperAdmin,
    userPermissions,
    userRole,
  };
}

/**
 * Hook for working with available roles.
 * Provides access to all roles and methods to filter them based on current user's permissions.
 */
export function useRoles() {
  const { allRoles, loading, error } = usePermissionContext();
  const { hasPermission, isSuperAdmin, isPlatformUser } = usePermission();

  /**
   * Get roles that the current user is allowed to assign to other users.
   * Filters based on the user's role and permissions.
   */
  const getAssignableRoles = useCallback((): RoleInfo[] => {
    if (!allRoles.length) return [];

    // Super admin can assign all roles
    if (isSuperAdmin) {
      return allRoles;
    }

    // Platform users (non-super admin) can assign all except super_admin
    if (isPlatformUser) {
      return allRoles.filter((role) => role.name !== Roles.SUPER_ADMIN);
    }

    // Tenant admin can only assign tenant-level roles (except tenant_admin)
    if (hasPermission('users:update_role')) {
      return allRoles.filter(
        (role) => role.level === RoleLevels.TENANT && role.name !== Roles.TENANT_ADMIN
      );
    }

    // No permission to assign roles
    return [];
  }, [allRoles, isSuperAdmin, isPlatformUser, hasPermission]);

  /**
   * Get a role by its name.
   */
  const getRoleByName = useCallback(
    (name: string): RoleInfo | undefined => {
      return allRoles.find((role) => role.name === name);
    },
    [allRoles]
  );

  /**
   * Get roles filtered by level.
   */
  const getRolesByLevel = useCallback(
    (level: RoleLevel | string): RoleInfo[] => {
      return allRoles.filter((role) => role.level === level);
    },
    [allRoles]
  );

  return {
    allRoles,
    loading,
    error,
    getAssignableRoles,
    getRoleByName,
    getRolesByLevel,
  };
}
