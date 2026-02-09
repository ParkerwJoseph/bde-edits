import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { permissionApi, type PermissionInfo, type RoleInfo } from '../api/permissionApi';

interface PermissionContextType {
  /** All available permissions in the system */
  allPermissions: PermissionInfo[];
  /** All available roles in the system */
  allRoles: RoleInfo[];
  /** Whether permissions/roles are still loading */
  loading: boolean;
  /** Any error that occurred during loading */
  error: string | null;
  /** Refresh permissions and roles from the backend */
  refresh: () => Promise<void>;
}

const PermissionContext = createContext<PermissionContextType | undefined>(undefined);

interface PermissionProviderProps {
  children: ReactNode;
}

export function PermissionProvider({ children }: PermissionProviderProps) {
  const [allPermissions, setAllPermissions] = useState<PermissionInfo[]>([]);
  const [allRoles, setAllRoles] = useState<RoleInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPermissionsAndRoles = async () => {
    try {
      setLoading(true);
      setError(null);
      const [permissions, roles] = await Promise.all([
        permissionApi.getPermissions(),
        permissionApi.getRoles(),
      ]);
      setAllPermissions(permissions);
      setAllRoles(roles);
    } catch (err) {
      console.error('Failed to load permissions and roles:', err);
      setError('Failed to load permissions and roles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPermissionsAndRoles();
  }, []);

  return (
    <PermissionContext.Provider
      value={{
        allPermissions,
        allRoles,
        loading,
        error,
        refresh: loadPermissionsAndRoles,
      }}
    >
      {children}
    </PermissionContext.Provider>
  );
}

export function usePermissionContext(): PermissionContextType {
  const context = useContext(PermissionContext);
  if (context === undefined) {
    throw new Error('usePermissionContext must be used within a PermissionProvider');
  }
  return context;
}
