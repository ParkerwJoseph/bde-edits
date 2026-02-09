/**
 * CustomerHealthGrid Component
 *
 * Displays key customer health metrics in a grid layout with sparklines.
 * Shows: Total Customers, New Signups, Churned, NRR, Renewal Rate, At-Risk.
 * Fetches real data from the metrics API.
 */

import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  UserPlus,
  UserMinus,
  RefreshCw,
  TrendingUp,
  AlertTriangle,
  ChevronRight,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react';
import { MetricSparkline } from './MetricSparkline';
import { useAnalyticsMetrics } from '../../hooks/useAnalyticsMetrics';
import { useCompany } from '../../contexts/CompanyContext';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/home/CustomerHealthGrid.module.css';

interface CustomerMetric {
  id: string;
  label: string;
  value: string;
  change: string;
  changeType: 'positive' | 'negative' | 'neutral';
  icon: LucideIcon;
  sparkData: number[];
  color: string;
}

// Map metric card IDs to display configuration for Customer Health metrics
const METRIC_CONFIG: Record<string, {
  label: string;
  icon: LucideIcon;
  color: string;
  formatValue: (val: number | null, unit: string | null) => string;
  isPositiveGood?: boolean;
}> = {
  'total-customers': {
    label: 'Total Customers',
    icon: Users,
    color: 'hsl(199, 89%, 48%)',
    formatValue: (val) => val !== null ? val.toLocaleString() : '—',
    isPositiveGood: true,
  },
  'new-signups': {
    label: 'New Signups',
    icon: UserPlus,
    color: 'hsl(142, 71%, 45%)',
    formatValue: (val) => val !== null ? `+${val.toLocaleString()}` : '—',
    isPositiveGood: true,
  },
  'churned-customers': {
    label: 'Churned',
    icon: UserMinus,
    color: 'hsl(0, 84%, 60%)',
    formatValue: (val) => val !== null ? val.toLocaleString() : '—',
    isPositiveGood: false,
  },
  'nrr-card': {
    label: 'NRR',
    icon: TrendingUp,
    color: 'hsl(142, 71%, 45%)',
    formatValue: (val) => val !== null ? `${val.toFixed(0)}%` : '—',
    isPositiveGood: true,
  },
  'renewal-rate': {
    label: 'Renewal Rate',
    icon: RefreshCw,
    color: 'hsl(199, 89%, 48%)',
    formatValue: (val) => val !== null ? `${val.toFixed(0)}%` : '—',
    isPositiveGood: true,
  },
  'at-risk-customers': {
    label: 'At-Risk',
    icon: ShieldAlert,
    color: 'hsl(45, 93%, 47%)',
    formatValue: (val) => val !== null ? val.toLocaleString() : '—',
    isPositiveGood: false,
  },
};

// Order of customer health metrics to display
const METRIC_ORDER = [
  'total-customers',
  'new-signups',
  'churned-customers',
  'nrr-card',
  'renewal-rate',
  'at-risk-customers',
];

// Generate mock sparkline data based on current value
function generateSparkData(currentValue: number | null): number[] {
  if (currentValue === null) return [];
  // Generate 6 data points with slight variation
  const variance = currentValue * 0.1;
  return Array.from({ length: 6 }, (_, i) => {
    const progress = i / 5;
    const trend = currentValue * (0.85 + progress * 0.15);
    const randomVariance = (Math.random() - 0.5) * variance;
    return Math.max(0, trend + randomVariance);
  });
}

export function CustomerHealthGrid() {
  const navigate = useNavigate();
  const { selectedCompanyId } = useCompany();
  const { kpiData, isLoading } = useAnalyticsMetrics(selectedCompanyId);

  // Transform KPI data into display format
  const metrics = useMemo((): CustomerMetric[] => {
    return METRIC_ORDER
      .map((cardId) => {
        const config = METRIC_CONFIG[cardId];
        const data = kpiData[cardId];

        if (!config) return null;

        const numericValue = data?.numericValue ?? null;
        const displayValue = data?.value ?? config.formatValue(null, null);
        const sparkData = generateSparkData(numericValue);

        // Determine change type based on trend
        let changeType: 'positive' | 'negative' | 'neutral' = 'neutral';
        let changeText = 'No data';

        if (data?.change !== 0 && data?.change !== undefined) {
          const isPositive = data.change > 0;
          changeType = config.isPositiveGood
            ? (isPositive ? 'positive' : 'negative')
            : (isPositive ? 'negative' : 'positive');
          changeText = `${isPositive ? '+' : ''}${data.change}%`;
        } else if (data?.period) {
          changeText = data.period;
          changeType = 'neutral';
        }

        return {
          id: cardId,
          label: config.label,
          value: displayValue,
          change: changeText,
          changeType,
          icon: config.icon,
          sparkData,
          color: config.color,
        };
      })
      .filter((m): m is CustomerMetric => m !== null);
  }, [kpiData]);

  const handleClick = () => {
    navigate('/metrics/customer-health');
  };

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <span className={styles.title}>Customer Health</span>
        </div>
        <div className={styles.grid}>
          {METRIC_ORDER.slice(0, 6).map((id) => (
            <div key={id} className={styles.metricCard}>
              <div className={styles.metricLoading}>
                <div className={styles.loadingPulse} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const hasData = metrics.some(m => m.value !== '—');

  if (!hasData) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <span className={styles.title}>Customer Health</span>
        </div>
        <div className={styles.emptyState}>
          <AlertTriangle size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No customer health data available</p>
          <p className={styles.emptySubtext}>Upload documents or connect data sources to extract metrics</p>
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
        <span className={styles.title}>Customer Health</span>
        <ChevronRight size={16} className={styles.chevron} />
      </div>
      <div className={styles.grid}>
        {metrics.map((metric) => {
          const Icon = metric.icon;
          const hasValue = metric.value !== '—';

          return (
            <div key={metric.id} className={styles.metricCard}>
              <div className={styles.metricHeader}>
                <div
                  className={styles.metricIconWrapper}
                  style={{ backgroundColor: `${metric.color}15` }}
                >
                  <Icon size={14} style={{ color: metric.color }} />
                </div>
                <span className={styles.metricLabel}>{metric.label}</span>
              </div>
              <p className={styles.metricValue}>{metric.value}</p>
              {hasValue && metric.sparkData.length > 0 && (
                <div className={styles.sparklineWrapper}>
                  <MetricSparkline data={metric.sparkData} color={metric.color} height={32} />
                </div>
              )}
              <p
                className={cn(
                  styles.metricChange,
                  metric.changeType === 'positive' && styles.changePositive,
                  metric.changeType === 'negative' && styles.changeNegative,
                  metric.changeType === 'neutral' && styles.changeNeutral
                )}
              >
                {metric.change}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default CustomerHealthGrid;
