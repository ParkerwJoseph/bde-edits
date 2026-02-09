import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { usePermission } from '../../hooks/usePermission';
import { getNavRoutesBySection, type RouteConfig } from '../../routes/routeConfig';
import styles from '../../styles/components/layout/Sidebar.module.css';

const ROLE_LABELS: Record<string, string> = {
  super_admin: 'Super Admin',
  bcp_analyst: 'BCP Analyst',
  tenant_admin: 'Tenant Admin',
  tenant_user: 'Tenant User',
};

export default function Sidebar() {
  const { user, logout } = useAuth();
  const { hasAnyPermission } = usePermission();

  const companyName = user?.tenant?.company_name || 'BDE';
  const userName = user?.display_name || user?.email || 'User';
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  const roleName = user?.role?.name ? ROLE_LABELS[user.role.name] || user.role.name : '';

  const handleLogout = async () => {
    await logout();
  };

  /**
   * Check if a route should be visible to the current user.
   */
  const canAccessRoute = (route: RouteConfig): boolean => {
    // If no permissions required, everyone can access
    if (!route.permissions || route.permissions.length === 0) {
      return true;
    }
    // Check if user has any of the required permissions
    return hasAnyPermission(route.permissions);
  };

  const routesBySection = getNavRoutesBySection();

  // Filter routes based on user permissions
  const mainRoutes = routesBySection.main.filter(canAccessRoute);
  const managementRoutes = routesBySection.management.filter(canAccessRoute);
  const accountRoutes = routesBySection.account.filter(canAccessRoute);

  const renderNavLink = (route: RouteConfig) => (
    <NavLink
      key={route.path}
      to={route.path}
      className={({ isActive }) =>
        `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`
      }
      end={route.path === '/'}
    >
      <span className={styles.navIcon}>{route.navIcon}</span>
      {route.navLabel}
    </NavLink>
  );

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <h1 className={styles.logoTitle}>{companyName}</h1>
        <p className={styles.logoSubtitle}>Business Dashboard</p>
      </div>

      <nav className={styles.nav}>
        {mainRoutes.length > 0 && (
          <div className={styles.navSection}>
            <div className={styles.navSectionTitle}>Main</div>
            {mainRoutes.map(renderNavLink)}
          </div>
        )}

        {managementRoutes.length > 0 && (
          <div className={styles.navSection}>
            <div className={styles.navSectionTitle}>Management</div>
            {managementRoutes.map(renderNavLink)}
          </div>
        )}

        {accountRoutes.length > 0 && (
          <div className={styles.navSection}>
            <div className={styles.navSectionTitle}>Account</div>
            {accountRoutes.map(renderNavLink)}
          </div>
        )}
      </nav>

      <div className={styles.userSection}>
        <div className={styles.userInfo}>
          <div className={styles.userAvatar}>{userInitials}</div>
          <div className={styles.userDetails}>
            <div className={styles.userName}>{userName}</div>
            <div className={styles.userRole}>{roleName}</div>
          </div>
        </div>
        <button onClick={handleLogout} className={styles.logoutButton}>
          Sign Out
        </button>
      </div>
    </aside>
  );
}
