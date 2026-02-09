import type { ComponentType } from 'react';
import { Permissions, type Permission } from '../constants/permissions';

// Lazy load page components
import Login from '../pages/Login';
import Tenants from '../pages/Tenants';
import Users from '../pages/Users';
import Companies from '../pages/Companies';
import Upload from '../pages/Upload';
import DocumentDetail from '../pages/DocumentDetail';
import Copilot from '../pages/Copilot';
import Settings from '../pages/Settings';
import PromptManagement from '../pages/PromptManagement';
import Onboarding from '../pages/Onboarding';
import Forbidden from '../pages/Forbidden';
import Connectors from '../pages/Connectors';
import {
  PillarScoresDetail,
  SinglePillarDetail,
  RiskRadarDetail,
  QuickStatsDetail,
  CustomerHealthDetail,
  ProductHealthDetail,
} from '../pages/scoring';
import Analytics from '../pages/Analytics';
import AnalyticsPillarDetail from '../pages/AnalyticsPillarDetail';
import MetricDetail from '../pages/MetricDetail';
import SignalDetail from '../pages/SignalDetail';
import Home from '../pages/Home';
import Ingestion from '../pages/Ingestion';
import Analysis from '../pages/Analysis';

/**
 * Route configuration with permission requirements.
 */
export interface RouteConfig {
  /** URL path for the route */
  path: string;
  /** Page component to render */
  element: ComponentType;
  /** Whether this route is public (no auth required) */
  public?: boolean;
  /** Show in sidebar navigation */
  showInNav?: boolean;
  /** Navigation label (for sidebar) */
  navLabel?: string;
  /** Navigation icon (for sidebar) */
  navIcon?: string;
  /** Navigation section (for sidebar grouping) */
  navSection?: 'main' | 'management' | 'account';
  /** Required permissions - user needs ANY of these */
  permissions?: (Permission | string)[];
  /** Required permissions - user needs ALL of these */
  allPermissions?: (Permission | string)[];
  /** Required roles - user needs ANY of these */
  roles?: string[];
}

/**
 * All application routes with their configurations.
 * This is the single source of truth for routing and navigation.
 */
export const routes: RouteConfig[] = [
  // Public routes
  {
    path: '/login',
    element: Login,
    public: true,
  },
  {
    path: '/onboarding/:code',
    element: Onboarding,
    public: true,
  },
  {
    path: '/forbidden',
    element: Forbidden,
    public: false,
    showInNav: false,
  },

  // Main section
  {
    path: '/',
    element: Home,
    showInNav: true,
    navLabel: 'Home',
    navIcon: '🏠',
    navSection: 'main',
  },
  {
    path: '/analytics',
    element: Analytics,
    showInNav: true,
    navLabel: 'Analytics',
    navIcon: '📊',
    navSection: 'main',
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/analytics/pillar/:pillarId',
    element: AnalyticsPillarDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/metrics/:metricId',
    element: MetricDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/signals/:signalId',
    element: SignalDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/copilot',
    element: Copilot,
    showInNav: true,
    navLabel: 'AI Analyst',
    navIcon: '🤖',
    navSection: 'main',
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/ingestion',
    element: Ingestion,
    showInNav: true,
    navLabel: 'Ingestion',
    navIcon: '📥',
    navSection: 'main',
    permissions: [Permissions.FILES_UPLOAD, Permissions.FILES_READ],
  },
  {
    path: '/analysis',
    element: Analysis,
    showInNav: true,
    navLabel: 'Run Analysis',
    navIcon: '🔬',
    navSection: 'main',
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/connectors',
    element: Connectors,
    showInNav: true,
    navLabel: 'Connectors',
    navIcon: '🔗',
    navSection: 'main',
    permissions: [Permissions.CONNECTORS_READ, Permissions.CONNECTORS_MANAGE],
  },
  {
    path: '/upload',
    element: Upload,
    showInNav: false,
    navLabel: 'Upload Documents',
    navIcon: '📄',
    navSection: 'main',
    permissions: [Permissions.FILES_UPLOAD, Permissions.FILES_READ],
  },
  {
    path: '/documents/:documentId',
    element: DocumentDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/companies',
    element: Companies,
    showInNav: false,  // Hidden - using dropdown in sidebar
    navLabel: 'Companies',
    navIcon: '🏛️',
    navSection: 'main',
    permissions: [Permissions.FILES_READ],
  },

  // Scoring detail routes
  {
    path: '/scoring/:companyId/pillar-scores',
    element: PillarScoresDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/scoring/:companyId/pillars/:pillar',
    element: SinglePillarDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/scoring/:companyId/risk-radar',
    element: RiskRadarDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/scoring/:companyId/quick-stats',
    element: QuickStatsDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/scoring/:companyId/customer-health',
    element: CustomerHealthDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },
  {
    path: '/scoring/:companyId/product-health',
    element: ProductHealthDetail,
    showInNav: false,
    permissions: [Permissions.FILES_READ],
  },

  // Management section
  {
    path: '/tenants',
    element: Tenants,
    showInNav: true,
    navLabel: 'Tenants',
    navIcon: '🏢',
    navSection: 'management',
    permissions: [Permissions.TENANTS_READ_ALL],
  },
  {
    path: '/users',
    element: Users,
    showInNav: true,
    navLabel: 'Users',
    navIcon: '👥',
    navSection: 'management',
    permissions: [Permissions.USERS_READ_ALL, Permissions.USERS_READ_TENANT],
  },
  {
    path: '/prompts',
    element: PromptManagement,
    showInNav: true,
    navLabel: 'Prompt Management',
    navIcon: '📝',
    navSection: 'management',
    permissions: [Permissions.SETTINGS_READ],
  },

  // Account section
  {
    path: '/settings',
    element: Settings,
    showInNav: true,
    navLabel: 'Settings',
    navIcon: '⚙️',
    navSection: 'account',
  },
];

/**
 * Get routes that should appear in the navigation sidebar.
 */
export function getNavRoutes(): RouteConfig[] {
  return routes.filter((route) => route.showInNav);
}

/**
 * Get routes grouped by navigation section.
 */
export function getNavRoutesBySection(): Record<string, RouteConfig[]> {
  const navRoutes = getNavRoutes();
  return {
    main: navRoutes.filter((r) => r.navSection === 'main'),
    management: navRoutes.filter((r) => r.navSection === 'management'),
    account: navRoutes.filter((r) => r.navSection === 'account'),
  };
}
