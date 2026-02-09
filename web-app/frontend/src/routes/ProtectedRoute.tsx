import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePermission } from '../hooks/usePermission';
import Loader from '../components/common/Loader';
import type { ReactNode } from 'react';
import type { Permission } from '../constants/permissions';

interface ProtectedRouteProps {
  children: ReactNode;
  /** Required permissions - user needs ANY of these to access */
  permissions?: (Permission | string)[];
  /** Required permissions - user needs ALL of these to access */
  allPermissions?: (Permission | string)[];
  /** Required roles - user needs ANY of these to access */
  roles?: string[];
}

export default function ProtectedRoute({
  children,
  permissions,
  allPermissions,
  roles,
}: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const { hasAnyPermission, hasAllPermissions, hasRole } = usePermission();

  if (loading) {
    return <Loader size="large" fullScreen text="Loading..." />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Check permissions (ANY)
  if (permissions && permissions.length > 0) {
    if (!hasAnyPermission(permissions)) {
      return <Navigate to="/forbidden" replace />;
    }
  }

  // Check permissions (ALL)
  if (allPermissions && allPermissions.length > 0) {
    if (!hasAllPermissions(allPermissions)) {
      return <Navigate to="/forbidden" replace />;
    }
  }

  // Check roles
  if (roles && roles.length > 0) {
    if (!hasRole(roles)) {
      return <Navigate to="/forbidden" replace />;
    }
  }

  return <>{children}</>;
}
