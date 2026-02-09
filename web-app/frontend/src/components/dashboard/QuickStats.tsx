import { useNavigate } from 'react-router-dom';
import styles from '../../styles/components/dashboard/QuickStats.module.css';
import { formatCurrency } from '../../api/scoringApi';
import type { MetricsResponse } from '../../api/scoringApi';

interface QuickStatsProps {
  metrics: MetricsResponse | null;
  companyId: string | null;
  onClick?: () => void;
}

interface StatItem {
  label: string;
  value: string;
  subtext?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export default function QuickStats({ metrics, companyId, onClick }: QuickStatsProps) {
  const navigate = useNavigate();
  const isPlaceholder = !metrics;

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (companyId) {
      navigate(`/scoring/${companyId}/metrics`);
    }
  };

  // Extract key metrics for quick view
  const getStats = (): StatItem[] => {
    if (!metrics) {
      return [
        { label: 'ARR', value: '--', subtext: 'No data' },
        { label: 'MRR', value: '--', subtext: 'No data' },
        { label: 'Runway', value: '--', subtext: 'No data' },
        { label: 'Burn Rate', value: '--', subtext: 'No data' },
        { label: 'CAC', value: '--', subtext: 'No data' },
        { label: 'LTV', value: '--', subtext: 'No data' },
      ];
    }

    const m = metrics.metrics;

    return [
      {
        label: 'ARR',
        value: m.ARR?.current_value.numeric
          ? formatCurrency(m.ARR.current_value.numeric)
          : '--',
        subtext: 'Annual Recurring Revenue',
        trend: 'up' as const
      },
      {
        label: 'MRR',
        value: m.MRR?.current_value.numeric
          ? formatCurrency(m.MRR.current_value.numeric)
          : '--',
        subtext: 'Monthly Recurring Revenue'
      },
      {
        label: 'Runway',
        value: m.RunwayMonths?.current_value.numeric
          ? `${m.RunwayMonths.current_value.numeric} months`
          : '--',
        subtext: 'Cash Runway'
      },
      {
        label: 'Burn Rate',
        value: m.BurnRateMonthly?.current_value.numeric
          ? `${formatCurrency(m.BurnRateMonthly.current_value.numeric)}/mo`
          : '--',
        subtext: 'Monthly Burn'
      },
      {
        label: 'CAC',
        value: m.CAC?.current_value.numeric
          ? formatCurrency(m.CAC.current_value.numeric)
          : '--',
        subtext: 'Customer Acquisition Cost'
      },
      {
        label: 'Sales Cycle',
        value: m.AvgSalesCycleDays?.current_value.numeric
          ? `${m.AvgSalesCycleDays.current_value.numeric} days`
          : '--',
        subtext: 'Average Days to Close'
      },
    ];
  };

  const stats = getStats();

  return (
    <div className={styles.container} onClick={handleClick}>
      <div className={styles.header}>
        <h3 className={styles.title}>Quick Stats</h3>
        <span className={styles.viewMore}>View All Metrics &rarr;</span>
      </div>

      <div className={styles.statsGrid}>
        {stats.map((stat, idx) => (
          <div
            key={idx}
            className={`${styles.statCard} ${isPlaceholder ? styles.placeholder : ''}`}
          >
            <span className={styles.statValue}>{stat.value}</span>
            <span className={styles.statLabel}>{stat.label}</span>
            {stat.subtext && (
              <span className={styles.statSubtext}>{stat.subtext}</span>
            )}
            {stat.trend && (
              <span className={`${styles.trend} ${styles[stat.trend]}`}>
                {stat.trend === 'up' ? '↑' : stat.trend === 'down' ? '↓' : '→'}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
