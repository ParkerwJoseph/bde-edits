import { useNavigate } from 'react-router-dom';
import styles from '../../styles/components/dashboard/HealthPanel.module.css';
import type { MetricsResponse } from '../../api/scoringApi';

interface CustomerHealthPanelProps {
  metrics: MetricsResponse | null;
  companyId: string | null;
  onClick?: () => void;
}

interface MetricDisplay {
  label: string;
  value: string;
  status: 'good' | 'warning' | 'bad' | 'neutral';
}

export default function CustomerHealthPanel({ metrics, companyId, onClick }: CustomerHealthPanelProps) {
  const navigate = useNavigate();
  const isPlaceholder = !metrics;

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (companyId) {
      navigate(`/scoring/${companyId}/customer-health`);
    }
  };

  const getMetrics = (): MetricDisplay[] => {
    if (!metrics) {
      return [
        { label: 'Total Customers', value: '--', status: 'neutral' },
        { label: 'New Signups', value: '--', status: 'neutral' },
        { label: 'At-Risk', value: '--', status: 'neutral' },
        { label: 'NRR', value: '--', status: 'neutral' },
        { label: 'GRR', value: '--', status: 'neutral' },
        { label: 'Churn Rate', value: '--', status: 'neutral' },
      ];
    }

    const m = metrics.metrics;

    const getNRRStatus = (val: number): 'good' | 'warning' | 'bad' => {
      if (val >= 110) return 'good';
      if (val >= 95) return 'warning';
      return 'bad';
    };

    const getGRRStatus = (val: number): 'good' | 'warning' | 'bad' => {
      if (val >= 90) return 'good';
      if (val >= 80) return 'warning';
      return 'bad';
    };

    const getChurnStatus = (val: number): 'good' | 'warning' | 'bad' => {
      if (val <= 5) return 'good';
      if (val <= 10) return 'warning';
      return 'bad';
    };

    return [
      {
        label: 'Total Customers',
        value: m.TotalCustomers?.current_value.numeric?.toString() ?? '--',
        status: 'neutral'
      },
      {
        label: 'New Signups',
        value: m.NewSignups?.current_value.numeric?.toString() ?? '--',
        status: 'neutral'
      },
      {
        label: 'At-Risk Accounts',
        value: m.AtRiskCustomerCount?.current_value.numeric?.toString() ?? '--',
        status: m.AtRiskCustomerCount?.current_value.numeric ? 'warning' : 'neutral'
      },
      {
        label: 'NRR',
        value: m.NRR?.current_value.numeric ? `${m.NRR.current_value.numeric}%` : '--',
        status: m.NRR?.current_value.numeric ? getNRRStatus(m.NRR.current_value.numeric) : 'neutral'
      },
      {
        label: 'GRR',
        value: m.GRR?.current_value.numeric ? `${m.GRR.current_value.numeric}%` : '--',
        status: m.GRR?.current_value.numeric ? getGRRStatus(m.GRR.current_value.numeric) : 'neutral'
      },
      {
        label: 'Churn Rate',
        value: m.ChurnRatePct?.current_value.numeric ? `${m.ChurnRatePct.current_value.numeric}%` : '--',
        status: m.ChurnRatePct?.current_value.numeric ? getChurnStatus(m.ChurnRatePct.current_value.numeric) : 'neutral'
      },
    ];
  };

  const displayMetrics = getMetrics();

  return (
    <div className={styles.container} onClick={handleClick}>
      <div className={styles.header}>
        <h3 className={styles.title}>Customer Health</h3>
        <span className={styles.viewMore}>View Details &rarr;</span>
      </div>

      <div className={styles.metricsGrid}>
        {displayMetrics.map((metric, idx) => (
          <div
            key={idx}
            className={`${styles.metricCard} ${isPlaceholder ? styles.placeholder : ''}`}
          >
            <span className={`${styles.metricValue} ${styles[metric.status]}`}>
              {metric.value}
            </span>
            <span className={styles.metricLabel}>{metric.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
