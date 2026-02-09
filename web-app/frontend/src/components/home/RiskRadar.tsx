/**
 * RiskRadar Component
 *
 * Displays active risks across all pillars with severity indicators.
 * Fetches real data from the flags API.
 */

import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronRight,
} from 'lucide-react';
import { useFlags } from '../../hooks/useScoring';
import { useCompany } from '../../contexts/CompanyContext';
import { PILLAR_CONFIG, type BDEPillar } from '../../api/scoringApi';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/home/RiskRadar.module.css';

interface RiskItem {
  id: string;
  severity: 'high' | 'medium' | 'low';
  title: string;
  pillar: string;
  category: string;
}

const SEVERITY_CONFIG = {
  high: {
    icon: AlertTriangle,
    className: styles.severityHigh,
    badgeClass: styles.badgeHigh,
    label: 'High',
  },
  medium: {
    icon: AlertCircle,
    className: styles.severityMedium,
    badgeClass: styles.badgeMedium,
    label: 'Med',
  },
  low: {
    icon: Info,
    className: styles.severityLow,
    badgeClass: styles.badgeLow,
    label: 'Low',
  },
};

export function RiskRadar() {
  const navigate = useNavigate();
  const { selectedCompanyId } = useCompany();
  const { data: flagsData, isLoading } = useFlags(selectedCompanyId);

  // Transform flags data into risk items
  const risks = useMemo((): RiskItem[] => {
    if (!flagsData) return [];

    const allRisks: RiskItem[] = [];

    // Red flags = high severity
    flagsData.red_flags.forEach((flag, index) => {
      allRisks.push({
        id: `red-${index}`,
        severity: 'high',
        title: flag.text.length > 50 ? flag.text.substring(0, 50) + '...' : flag.text,
        pillar: flag.pillar ? PILLAR_CONFIG[flag.pillar as BDEPillar]?.label || flag.pillar : 'General',
        category: flag.category,
      });
    });

    // Yellow flags = medium severity
    flagsData.yellow_flags.forEach((flag, index) => {
      allRisks.push({
        id: `yellow-${index}`,
        severity: 'medium',
        title: flag.text.length > 50 ? flag.text.substring(0, 50) + '...' : flag.text,
        pillar: flag.pillar ? PILLAR_CONFIG[flag.pillar as BDEPillar]?.label || flag.pillar : 'General',
        category: flag.category,
      });
    });

    // Limit to 6 risks for display
    return allRisks.slice(0, 6);
  }, [flagsData]);

  // Count by severity
  const counts = useMemo(() => {
    const redCount = flagsData?.red_flags.length || 0;
    const yellowCount = flagsData?.yellow_flags.length || 0;
    return {
      high: redCount,
      medium: yellowCount,
      low: 0, // No low severity in current API
    };
  }, [flagsData]);

  const handleClick = () => {
    navigate('/metrics/risk-radar');
  };

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <span className={styles.title}>Risk Radar</span>
        </div>
        <div className={styles.grid}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={styles.riskItem}>
              <div className={styles.loadingPulse} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (risks.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <span className={styles.title}>Risk Radar</span>
        </div>
        <div className={styles.emptyState}>
          <Info size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No active risks detected</p>
          <p className={styles.emptySubtext}>Run analysis to identify potential risks</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={styles.container}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
    >
      <div className={styles.header}>
        <span className={styles.title}>Risk Radar</span>
        <div className={styles.badges}>
          {counts.high > 0 && (
            <span className={cn(styles.badge, styles.badgeHigh)}>
              {counts.high} High
            </span>
          )}
          {counts.medium > 0 && (
            <span className={cn(styles.badge, styles.badgeMedium)}>
              {counts.medium} Med
            </span>
          )}
          {counts.low > 0 && (
            <span className={cn(styles.badge, styles.badgeLow)}>
              {counts.low} Low
            </span>
          )}
          <ChevronRight size={16} className={styles.chevron} />
        </div>
      </div>
      <div className={styles.grid}>
        {risks.map((risk) => {
          const config = SEVERITY_CONFIG[risk.severity];
          const Icon = config.icon;

          return (
            <div
              key={risk.id}
              className={cn(styles.riskItem, config.className)}
            >
              <Icon size={20} className={styles.riskIcon} />
              <div className={styles.riskContent}>
                <p className={styles.riskTitle}>{risk.title}</p>
                <p className={styles.riskMeta}>
                  {risk.pillar} <span className={styles.bullet}>•</span> {risk.category}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RiskRadar;
