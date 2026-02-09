/**
 * AppSidebar Component
 *
 * New sidebar with company selector, collapsible mode, and updated visual design.
 * Preserves existing permission checks and route configuration.
 */

import { useState, useEffect, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Upload,
  Sparkles,
  Building2,
  Link2,
  Users,
  Building,
  FileText,
  Settings,
  LogOut,
  ChevronDown,
  Shield,
  Check,
  Loader2,
  Plus,
  X,
  BarChart3,
  Play,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { usePermission } from '../../hooks/usePermission';
import { useCompany } from '../../contexts/CompanyContext';
import { getNavRoutesBySection, type RouteConfig } from '../../routes/routeConfig';
import { Avatar, AvatarFallback } from '../ui/Avatar';
import { Button } from '../ui/Button';
import { Separator } from '../ui/Separator';
import { ScrollArea } from '../ui/ScrollArea';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/Tooltip';
import { cn } from '../../lib/scorecard-utils';
import { companyApi } from '../../api/companyApi';
import bdeLogo from '../../assets/bde-logo.png';
import styles from '../../styles/components/layout/AppSidebar.module.css';

// Helper to get initials from a name
function getInitials(name: string): string {
  return name
    .split(' ')
    .map(part => part.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

// Icon mapping for nav items (emoji to lucide-react icon)
const NAV_ICONS: Record<string, typeof LayoutDashboard> = {
  '🏠': LayoutDashboard,
  '📊': BarChart3,
  '🤖': Sparkles,
  '📥': Upload,
  '🔬': Play,
  '🔗': Link2,
  '📄': Upload,
  '🏛️': Building2,
  '🏢': Building,
  '👥': Users,
  '📝': FileText,
  '⚙️': Settings,
};

const ROLE_LABELS: Record<string, string> = {
  super_admin: 'Super Admin',
  bcp_analyst: 'BCP Analyst',
  tenant_admin: 'Tenant Admin',
  tenant_user: 'Tenant User',
};

export interface AppSidebarProps {
  /** Whether sidebar is collapsed */
  collapsed?: boolean;
  /** Callback when collapsed state changes */
  onCollapsedChange?: (collapsed: boolean) => void;
}

export function AppSidebar({ collapsed = false, onCollapsedChange: _onCollapsedChange }: AppSidebarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { hasAnyPermission } = usePermission();
  const {
    selectedCompanyId,
    selectedCompany,
    companies,
    isLoading: isLoadingCompanies,
    selectCompany,
    addCompany,
  } = useCompany();
  const [companyDropdownOpen, setCompanyDropdownOpen] = useState(false);
  const [showAddCompanyForm, setShowAddCompanyForm] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [isCreatingCompany, setIsCreatingCompany] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const newCompanyInputRef = useRef<HTMLInputElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setCompanyDropdownOpen(false);
      }
    };

    if (companyDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [companyDropdownOpen]);

  // Handle company selection
  const handleSelectCompany = (companyId: string) => {
    selectCompany(companyId);
    setCompanyDropdownOpen(false);
  };

  // Handle opening add company form
  const handleShowAddForm = () => {
    setShowAddCompanyForm(true);
    // Focus input after render
    setTimeout(() => {
      newCompanyInputRef.current?.focus();
    }, 0);
  };

  // Handle canceling add company form
  const handleCancelAddCompany = () => {
    setShowAddCompanyForm(false);
    setNewCompanyName('');
  };

  // Handle creating a new company
  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = newCompanyName.trim();
    if (!trimmedName) return;

    setIsCreatingCompany(true);
    try {
      const newCompany = await companyApi.create({ name: trimmedName });
      // Add new company to context and select it
      addCompany(newCompany);
      selectCompany(newCompany.id);
      // Reset form
      setNewCompanyName('');
      setShowAddCompanyForm(false);
    } catch (error) {
      console.error('Failed to create company:', error);
    } finally {
      setIsCreatingCompany(false);
    }
  };

  // Get selected company name
  const displayCompanyName = selectedCompany?.name || user?.tenant?.company_name || 'BDE';

  // User info
  const userName = user?.display_name || user?.email || 'User';
  const userInitials = getInitials(userName);
  const roleName = user?.role?.name ? ROLE_LABELS[user.role.name] || user.role.name : '';

  // Route permissions check
  const canAccessRoute = (route: RouteConfig): boolean => {
    if (!route.permissions || route.permissions.length === 0) {
      return true;
    }
    return hasAnyPermission(route.permissions);
  };

  const routesBySection = getNavRoutesBySection();
  const mainRoutes = routesBySection.main.filter(canAccessRoute);
  const managementRoutes = routesBySection.management.filter(canAccessRoute);
  const accountRoutes = routesBySection.account.filter(canAccessRoute);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const renderNavLink = (route: RouteConfig) => {
    const IconComponent = NAV_ICONS[route.navIcon || ''] || LayoutDashboard;

    const linkContent = (
      <NavLink
        to={route.path}
        className={({ isActive }) => {
          if (collapsed) {
            // Collapsed mode: use special collapsed classes
            return isActive
              ? cn(styles.navLink, styles.navLinkCollapsedActive)
              : cn(styles.navLink, styles.navLinkCollapsed);
          }
          // Expanded mode: use normal classes
          return cn(
            styles.navLink,
            isActive && styles.navLinkActive
          );
        }}
        end={route.path === '/'}
      >
        <IconComponent className={styles.navIcon} size={collapsed ? 20 : 16} />
        {!collapsed && <span className={styles.navLabel}>{route.navLabel}</span>}
      </NavLink>
    );

    if (collapsed) {
      return (
        <TooltipProvider key={route.path}>
          <Tooltip>
            <TooltipTrigger asChild>
              {linkContent}
            </TooltipTrigger>
            <TooltipContent side="right">
              {route.navLabel}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return <div key={route.path}>{linkContent}</div>;
  };

  return (
    <aside className={cn(styles.sidebar, collapsed && styles.sidebarCollapsed)}>
      {/* Header */}
      <div className={styles.header}>
        {collapsed ? (
          <div className={styles.logoCollapsed}>
            <img src={bdeLogo} alt="BDE" className={styles.logoImageSmall} />
          </div>
        ) : (
          <div className={styles.headerContent}>
            {/* Logo */}
            <div className={styles.logo}>
              <img src={bdeLogo} alt="BDE" className={styles.logoImage} />
              <span className={styles.logoText}>BDE</span>
            </div>

            {/* Company Selector */}
            <div className={styles.companySelector} ref={dropdownRef}>
              <button
                className={styles.companySelectorButton}
                onClick={() => setCompanyDropdownOpen(!companyDropdownOpen)}
              >
                <div className={styles.companyInfo}>
                  <span className={styles.companyName}>{displayCompanyName}</span>
                  <span className={styles.companyType}>
                    {companies.length > 0 ? `${companies.length} Companies` : 'Business Dashboard'}
                  </span>
                </div>
                {isLoadingCompanies ? (
                  <Loader2 size={16} className={styles.companySelectorLoading} />
                ) : (
                  <ChevronDown
                    size={16}
                    className={cn(
                      styles.companySelectorIcon,
                      companyDropdownOpen && styles.companySelectorIconOpen
                    )}
                  />
                )}
              </button>

              {/* Company Dropdown */}
              {companyDropdownOpen && (
                <div className={styles.companyDropdown}>
                  {isLoadingCompanies ? (
                    <div className={styles.companyDropdownLoading}>
                      <Loader2 size={16} className={styles.companySelectorLoading} />
                      <span>Loading companies...</span>
                    </div>
                  ) : (
                    <>
                      {companies.length === 0 ? (
                        <div className={styles.companyDropdownEmpty}>
                          <span>No companies found</span>
                        </div>
                      ) : (
                        <div className={styles.companyDropdownList}>
                          {companies.map((company) => {
                            const isSelected = company.id === selectedCompanyId;
                            return (
                              <button
                                key={company.id}
                                className={cn(
                                  styles.companyOption,
                                  isSelected && styles.companyOptionActive
                                )}
                                onClick={() => handleSelectCompany(company.id)}
                              >
                                <div className={styles.companyOptionInfo}>
                                  <span className={styles.companyOptionName}>{company.name}</span>
                                  <span className={styles.companyOptionType}>
                                    {isSelected ? 'Selected' : 'Company'}
                                  </span>
                                </div>
                                {isSelected && <Check size={16} className={styles.companyOptionCheck} />}
                              </button>
                            );
                          })}
                        </div>
                      )}

                      {/* Add Company Section */}
                      <div className={styles.addCompanySection}>
                        {showAddCompanyForm ? (
                          <form
                            className={styles.addCompanyForm}
                            onSubmit={handleCreateCompany}
                          >
                            <input
                              ref={newCompanyInputRef}
                              type="text"
                              className={styles.addCompanyInput}
                              placeholder="Company name"
                              value={newCompanyName}
                              onChange={(e) => setNewCompanyName(e.target.value)}
                              disabled={isCreatingCompany}
                            />
                            <div className={styles.addCompanyActions}>
                              <button
                                type="submit"
                                className={styles.addCompanySubmit}
                                disabled={isCreatingCompany || !newCompanyName.trim()}
                              >
                                {isCreatingCompany ? (
                                  <Loader2 size={14} className={styles.companySelectorLoading} />
                                ) : (
                                  <Check size={14} />
                                )}
                              </button>
                              <button
                                type="button"
                                className={styles.addCompanyCancel}
                                onClick={handleCancelAddCompany}
                                disabled={isCreatingCompany}
                              >
                                <X size={14} />
                              </button>
                            </div>
                          </form>
                        ) : (
                          <button
                            className={styles.addCompanyButton}
                            onClick={handleShowAddForm}
                          >
                            <Plus size={16} />
                            <span>Add Company</span>
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <Separator />

      {/* Navigation */}
      <ScrollArea className={styles.nav}>
        {mainRoutes.length > 0 && (
          <div className={styles.navSection}>
            {!collapsed && <div className={styles.navSectionTitle}>Navigation</div>}
            <div className={styles.navList}>
              {mainRoutes.map(renderNavLink)}
            </div>
          </div>
        )}

        {managementRoutes.length > 0 && (
          <div className={styles.navSection}>
            {!collapsed && <div className={styles.navSectionTitle}>Management</div>}
            <div className={styles.navList}>
              {managementRoutes.map(renderNavLink)}
            </div>
          </div>
        )}

        {accountRoutes.length > 0 && (
          <div className={styles.navSection}>
            {!collapsed && <div className={styles.navSectionTitle}>Account</div>}
            <div className={styles.navList}>
              {accountRoutes.map(renderNavLink)}
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Footer */}
      <div className={styles.footer}>
        <Separator />

        {/* User Info */}
        <div className={cn(styles.userSection, collapsed && styles.userSectionCollapsed)}>
          <Avatar className="h-8 w-8">
            <AvatarFallback>{userInitials}</AvatarFallback>
          </Avatar>
          {!collapsed && (
            <div className={styles.userInfo}>
              <span className={styles.userName}>{userName}</span>
              <span className={styles.userRole}>
                <Shield size={12} />
                {roleName}
              </span>
            </div>
          )}
        </div>

        {/* Logout */}
        <div className={styles.footerActions}>
          {collapsed ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleLogout}
                    className={styles.logoutButton}
                  >
                    <LogOut size={18} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  Sign Out
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <Button
              variant="ghost"
              onClick={handleLogout}
              className={styles.logoutButton}
            >
              <LogOut size={16} />
              Sign Out
            </Button>
          )}
        </div>
      </div>
    </aside>
  );
}

export default AppSidebar;
