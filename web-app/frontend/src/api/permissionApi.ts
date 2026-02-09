import { api } from '../utils/api';
import type { RoleLevel } from '../constants/permissions';

/**
 * Permission information from the backend.
 */
export interface PermissionInfo {
  name: string;
  category: string;
  description: string;
}

/**
 * Role information from the backend.
 */
export interface RoleInfo {
  name: string;
  level: RoleLevel;
  label: string;
  description: string | null;
}

interface PermissionsResponse {
  permissions: PermissionInfo[];
}

interface RolesResponse {
  roles: RoleInfo[];
}

export const permissionApi = {
  /**
   * Fetch all available permissions from the backend.
   */
  getPermissions: async (): Promise<PermissionInfo[]> => {
    const response = await api.get<PermissionsResponse>('/api/auth/permissions');
    return response.data.permissions;
  },

  /**
   * Fetch all available roles from the backend.
   */
  getRoles: async (): Promise<RoleInfo[]> => {
    const response = await api.get<RolesResponse>('/api/auth/roles');
    return response.data.roles;
  },
};
