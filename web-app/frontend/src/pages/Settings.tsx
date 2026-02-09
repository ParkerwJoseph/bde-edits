/**
 * Settings Page
 *
 * Configuration page with tabs for:
 * - Appearance (theme, KPI status colors, chart colors)
 * - Scoring (score thresholds, valuation bands)
 * - Users & Roles (role definitions and permissions)
 * - Versioning (model, prompt, scoring rubric versions)
 *
 * Based on reference UI design.
 */

import { useState } from 'react';
import {
  Palette,
  Sliders,
  Users,
  GitBranch,
  Shield,
  Moon,
  Sun,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../hooks/useTheme';
import { AppLayout } from '../components/layout/AppLayout';
import styles from '../styles/Settings.module.css';

// Score thresholds
const SCORE_THRESHOLDS = {
  green: { min: 4.0 },
  yellow: { min: 2.5 },
} as const;

// Valuation bands
const VALUATION_BANDS = [
  { band: 'Premium', score: '4.5+', multiples: '8-12x' },
  { band: 'Strong', score: '4.0-4.4', multiples: '6-8x' },
  { band: 'Average', score: '3.0-3.9', multiples: '4-6x' },
  { band: 'Below Average', score: '2.0-2.9', multiples: '2-4x' },
  { band: 'Distressed', score: '<2.0', multiples: '0.5-2x' },
];

// Role definitions
const ROLES = {
  viewer: {
    label: 'Viewer',
    description: 'Can view scorecards and analysis results',
    permissions: ['view'],
  },
  analyst: {
    label: 'Analyst',
    description: 'Can run analyses and manage evidence',
    permissions: ['view', 'run_analysis', 'manage_evidence'],
  },
  editor: {
    label: 'Editor',
    description: 'Can create companies and upload documents',
    permissions: ['view', 'run_analysis', 'manage_evidence', 'create_company', 'upload_docs'],
  },
  admin: {
    label: 'Admin',
    description: 'Full access to all features and settings',
    permissions: ['view', 'run_analysis', 'manage_evidence', 'create_company', 'upload_docs', 'manage_users', 'manage_settings'],
  },
};

// KPI status colors for preview
const KPI_COLORS = [
  { label: 'Strong', cssVar: '--kpi-strong' },
  { label: 'Healthy', cssVar: '--kpi-healthy' },
  { label: 'Watch', cssVar: '--kpi-watch' },
  { label: 'At Risk', cssVar: '--kpi-at-risk' },
  { label: 'High Risk', cssVar: '--kpi-high-risk' },
];

// Chart colors for preview
const CHART_COLORS = [
  { label: 'Default', cssVar: '--color-primary' },
  { label: 'Secondary', cssVar: '--kpi-healthy' },
  { label: 'Highlight', cssVar: '--kpi-at-risk' },
  { label: 'Accent', cssVar: '--kpi-strong' },
  { label: 'Muted', cssVar: '--kpi-watch' },
];

type TabId = 'appearance' | 'scoring' | 'users' | 'versioning';

const TABS: Array<{ id: TabId; label: string; icon: typeof Palette }> = [
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'scoring', label: 'Scoring', icon: Sliders },
  { id: 'users', label: 'Users & Roles', icon: Users },
  { id: 'versioning', label: 'Versioning', icon: GitBranch },
];

export default function Settings() {
  const { user } = useAuth();
  const { isDark, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<TabId>('appearance');

  const isAdmin = user?.role?.name === 'super_admin' || user?.role?.name === 'tenant_admin';

  return (
    <AppLayout title="Settings">
      <div className={styles.container}>
        {/* Tab Navigation */}
        <div className={styles.tabsList}>
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className={styles.tabContent}>
          {/* ===== Appearance Tab ===== */}
          {activeTab === 'appearance' && (
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>Theme Settings</h3>
                <p className={styles.cardDescription}>Choose your preferred color mode</p>
              </div>
              <div className={styles.cardBody}>
                {/* Dark Mode Toggle */}
                <div className={styles.settingRow}>
                  <div className={styles.settingRowLeft}>
                    <div className={styles.settingIcon}>
                      {isDark ? <Moon size={20} /> : <Sun size={20} />}
                    </div>
                    <div>
                      <span className={styles.settingLabel}>Dark Mode</span>
                      <p className={styles.settingHint}>
                        {isDark ? 'Currently using dark theme' : 'Currently using light theme'}
                      </p>
                    </div>
                  </div>
                  <label className={styles.toggle}>
                    <input
                      type="checkbox"
                      checked={isDark}
                      onChange={(e) => setTheme(e.target.checked ? 'dark' : 'light')}
                    />
                    <span className={styles.toggleSlider} />
                  </label>
                </div>

                {/* KPI Status Colors */}
                <div className={styles.colorSection}>
                  <h4 className={styles.colorSectionTitle}>KPI Status Colors</h4>
                  <div className={styles.colorGrid}>
                    {KPI_COLORS.map((item) => (
                      <div key={item.label} className={styles.colorItem}>
                        <div
                          className={styles.colorSwatch}
                          style={{ backgroundColor: `hsl(var(${item.cssVar}))` }}
                        />
                        <span className={styles.colorLabel}>{item.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Chart Colors */}
                <div className={styles.colorSection}>
                  <h4 className={styles.colorSectionTitle}>Chart Colors</h4>
                  <div className={styles.colorGrid}>
                    {CHART_COLORS.map((item) => (
                      <div key={item.label} className={styles.colorItem}>
                        <div
                          className={styles.colorSwatch}
                          style={{ backgroundColor: item.cssVar === '--color-primary' ? 'var(--color-primary)' : `hsl(var(${item.cssVar}))` }}
                        />
                        <span className={styles.colorLabel}>{item.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ===== Scoring Tab ===== */}
          {activeTab === 'scoring' && (
            <div className={styles.twoColumnGrid}>
              {/* Score Thresholds */}
              <div className={styles.card}>
                <div className={styles.cardHeader}>
                  <h3 className={styles.cardTitle}>Score Thresholds</h3>
                  <p className={styles.cardDescription}>Configure R/Y/G color mappings for scores</p>
                </div>
                <div className={styles.cardBody}>
                  <div className={styles.thresholdItem}>
                    <label className={styles.thresholdLabel}>
                      <span className={styles.thresholdDot} style={{ backgroundColor: 'hsl(var(--kpi-strong))' }} />
                      Strong
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      defaultValue={SCORE_THRESHOLDS.green.min}
                      disabled={!isAdmin}
                      className={styles.thresholdInput}
                    />
                    <p className={styles.thresholdHint}>Minimum score for strong status</p>
                  </div>

                  <div className={styles.thresholdItem}>
                    <label className={styles.thresholdLabel}>
                      <span className={styles.thresholdDot} style={{ backgroundColor: 'hsl(var(--kpi-watch))' }} />
                      Watch
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      defaultValue={SCORE_THRESHOLDS.yellow.min}
                      disabled={!isAdmin}
                      className={styles.thresholdInput}
                    />
                    <p className={styles.thresholdHint}>Minimum score for watch status</p>
                  </div>

                  <div className={styles.thresholdItem}>
                    <label className={styles.thresholdLabel}>
                      <span className={styles.thresholdDot} style={{ backgroundColor: 'hsl(var(--kpi-high-risk))' }} />
                      High Risk
                    </label>
                    <p className={styles.thresholdHint}>Scores below watch threshold</p>
                  </div>

                  {isAdmin && (
                    <button className={styles.saveButton} disabled>
                      Save Changes
                    </button>
                  )}
                </div>
              </div>

              {/* Valuation Bands */}
              <div className={styles.card}>
                <div className={styles.cardHeader}>
                  <h3 className={styles.cardTitle}>Valuation Bands</h3>
                  <p className={styles.cardDescription}>Configure score-to-valuation multiple mappings</p>
                </div>
                <div className={styles.cardBody}>
                  {VALUATION_BANDS.map((item) => (
                    <div key={item.band} className={styles.bandRow}>
                      <div>
                        <span className={styles.bandName}>{item.band}</span>
                        <span className={styles.bandScore}>({item.score})</span>
                      </div>
                      <span className={styles.bandBadge}>{item.multiples}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ===== Users & Roles Tab ===== */}
          {activeTab === 'users' && (
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>Role Definitions</h3>
                <p className={styles.cardDescription}>User roles and their permissions</p>
              </div>
              <div className={styles.cardBody}>
                {Object.entries(ROLES).map(([key, role]) => (
                  <div key={key} className={styles.roleRow}>
                    <div className={styles.roleIcon}>
                      <Shield size={20} />
                    </div>
                    <div className={styles.roleInfo}>
                      <div className={styles.roleHeader}>
                        <span className={styles.roleName}>{role.label}</span>
                        <span className={styles.roleKeyBadge}>{key}</span>
                      </div>
                      <p className={styles.roleDescription}>{role.description}</p>
                      <div className={styles.permissionsList}>
                        {role.permissions.map((perm) => (
                          <span key={perm} className={styles.permissionBadge}>
                            {perm.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}

                {!isAdmin && (
                  <p className={styles.adminNote}>
                    <Shield size={16} />
                    Contact an admin to manage user roles
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ===== Versioning Tab ===== */}
          {activeTab === 'versioning' && (
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>Model & Prompt Versions</h3>
                <p className={styles.cardDescription}>Track versions for reproducibility</p>
              </div>
              <div className={styles.cardBody}>
                <div className={styles.versionRow}>
                  <div>
                    <span className={styles.versionLabel}>Model Version</span>
                    <p className={styles.versionHint}>Current AI model version</p>
                  </div>
                  <span className={styles.versionBadge}>v1.0</span>
                </div>
                <div className={styles.versionRow}>
                  <div>
                    <span className={styles.versionLabel}>Prompt Version</span>
                    <p className={styles.versionHint}>Analysis prompt template version</p>
                  </div>
                  <span className={styles.versionBadge}>v1.0</span>
                </div>
                <div className={styles.versionRow}>
                  <div>
                    <span className={styles.versionLabel}>Scoring Rubric</span>
                    <p className={styles.versionHint}>Valuation band configuration</p>
                  </div>
                  <span className={styles.versionBadge}>v1.0</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
