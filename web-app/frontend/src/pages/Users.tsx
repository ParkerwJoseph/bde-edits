import { useState, useEffect } from 'react';
import { userApi, type UserWithDetails } from '../api/userApi';
import { useAuth } from '../context/AuthContext';
import { useRoles } from '../hooks/usePermission';
import { PermissionGate } from '../components/common/PermissionGate';
import { Permissions } from '../constants/permissions';
import { AppLayout } from '../components/layout/AppLayout';
import Loader from '../components/common/Loader';
import styles from '../styles/Common.module.css';

export default function Users() {
  const { user: currentUser } = useAuth();
  const { allRoles, getAssignableRoles, loading: rolesLoading } = useRoles();

  const [users, setUsers] = useState<UserWithDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<UserWithDetails | null>(null);
  const [selectedRole, setSelectedRole] = useState('');

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await userApi.list();
      setUsers(response.users || []);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async () => {
    if (!editingUser || !selectedRole) return;
    try {
      await userApi.updateRole(editingUser.id, selectedRole);
      setEditingUser(null);
      setSelectedRole('');
      loadUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleStatusToggle = async (user: UserWithDetails) => {
    try {
      await userApi.updateStatus(user.id, !user.is_active);
      loadUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const openRoleEditor = (user: UserWithDetails) => {
    setEditingUser(user);
    setSelectedRole(user.role_name || '');
  };

  /**
   * Get a display label for a role name.
   */
  const getRoleLabel = (roleName: string | null): string => {
    if (!roleName) return '-';
    const role = allRoles.find((r) => r.name === roleName);
    return role?.label || roleName.replace('_', ' ').toUpperCase();
  };

  // Get roles that the current user can assign
  const assignableRoles = getAssignableRoles();

  return (
    <AppLayout title="Users" subtitle="Manage user accounts and roles">
      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <h2 className={styles.cardTitle}>All Users</h2>
        </div>

        {loading || rolesLoading ? (
          <Loader size="medium" text="Loading users..." />
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Company</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.display_name || '-'}</td>
                  <td>{user.email || '-'}</td>
                  <td>{user.tenant_name || '-'}</td>
                  <td>{getRoleLabel(user.role_name)}</td>
                  <td>
                    <span
                      className={`${styles.statusBadge} ${user.is_active ? styles.statusActive : styles.statusSuspended}`}
                    >
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>{user.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : '-'}</td>
                  <td>
                    {user.id !== currentUser?.id && (
                      <>
                        <PermissionGate permission={Permissions.USERS_UPDATE_ROLE}>
                          <button onClick={() => openRoleEditor(user)} className={styles.secondaryButton}>
                            Change Role
                          </button>
                        </PermissionGate>
                        <PermissionGate permission={Permissions.USERS_UPDATE}>
                          <button
                            onClick={() => handleStatusToggle(user)}
                            className={styles.secondaryButton}
                            style={{ marginLeft: '0.5rem' }}
                          >
                            {user.is_active ? 'Disable' : 'Enable'}
                          </button>
                        </PermissionGate>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Role Editor Modal */}
      {editingUser && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3>Change Role</h3>
            <p>
              <strong>User:</strong> {editingUser.display_name || editingUser.email}
            </p>
            <p>
              <strong>Current Role:</strong> {getRoleLabel(editingUser.role_name)}
            </p>
            <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value)} className={styles.input}>
              <option value="">Select Role</option>
              {assignableRoles.map((role) => (
                <option key={role.name} value={role.name}>
                  {role.label}
                </option>
              ))}
            </select>
            <div className={styles.modalActions}>
              <button onClick={() => setEditingUser(null)} className={styles.secondaryButton}>
                Cancel
              </button>
              <button onClick={handleRoleChange} className={styles.primaryButton}>
                Update Role
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
