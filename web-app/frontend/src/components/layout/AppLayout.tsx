/**
 * AppLayout Component
 *
 * Main layout wrapper with the new sidebar and responsive design.
 * Supports collapsed sidebar state persisted in localStorage.
 */

import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { Bell, PanelLeft } from 'lucide-react';
import { AppSidebar } from './AppSidebar';
import { Button } from '../ui/Button';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/Tooltip';
import { Separator } from '../ui/Separator';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/layout/AppLayout.module.css';

const SIDEBAR_COLLAPSED_KEY = 'bde-sidebar-collapsed';

export interface AppLayoutProps {
  /** Page content */
  children: ReactNode;
  /** Page title */
  title?: string;
  /** Page subtitle/description */
  subtitle?: string;
  /** Whether to show the header */
  showHeader?: boolean;
  /** Header right content (actions, etc.) */
  headerActions?: ReactNode;
  /** Additional class for main content */
  className?: string;
  /** Whether to hide the notification bell in the header */
  hideHeaderBell?: boolean;
}

export function AppLayout({
  children,
  title,
  subtitle,
  showHeader = true,
  headerActions,
  className,
  hideHeaderBell = false,
}: AppLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    return saved === 'true';
  });

  // Persist sidebar state
  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  // Toggle sidebar
  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  // Keyboard shortcut to toggle sidebar (Ctrl+B)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'b' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        toggleSidebar();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleSidebar]);

  return (
    <div className={styles.layout}>
      {/* Sidebar */}
      <AppSidebar
        collapsed={sidebarCollapsed}
        onCollapsedChange={setSidebarCollapsed}
      />

      {/* Main Content Area */}
      <main
        className={cn(
          styles.main,
          sidebarCollapsed && styles.mainExpanded,
          className
        )}
      >
        {/* Header */}
        {showHeader && (
          <header className={styles.header}>
            <div className={styles.headerLeft}>
              {/* Sidebar Toggle Trigger */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={toggleSidebar}
                      className={styles.sidebarTrigger}
                    >
                      <PanelLeft /> {/* Uses [&_svg]:size-4 from Button = 16px - matches reference UI */}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    {sidebarCollapsed ? 'Expand sidebar (Ctrl+B)' : 'Collapse sidebar (Ctrl+B)'}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <Separator orientation="vertical" className={styles.headerSeparator} />

              {title && (
                <div className={styles.titleSection}>
                  <h1 className={styles.title}>{title}</h1>
                  {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
                </div>
              )}
            </div>

            <div className={styles.headerRight}>
              {headerActions}

              {/* Notification Bell */}
              {!hideHeaderBell && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" className={styles.notificationButton}>
                        <Bell size={20} />
                        {/* Notification dot - can be conditionally rendered */}
                        {/* <span className={styles.notificationDot} /> */}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">
                      Notifications
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </header>
        )}

        {/* Page Content */}
        <div className={styles.content}>
          {children}
        </div>
      </main>
    </div>
  );
}

export default AppLayout;
