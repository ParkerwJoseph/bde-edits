import { useNavigate } from 'react-router-dom';
import styles from '../../styles/components/dashboard/HealthPanel.module.css';
import type { MetricsResponse } from '../../api/scoringApi';

interface ProductHealthPanelProps {
  metrics: MetricsResponse | null;
  companyId: string | null;
  onClick?: () => void;
}

interface MetricDisplay {
  label: string;
  value: string;
  status: 'good' | 'warning' | 'bad' | 'neutral';
}

export default function ProductHealthPanel({ metrics, companyId, onClick }: ProductHealthPanelProps) {
  const navigate = useNavigate();
  const isPlaceholder = !metrics;

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (companyId) {
      navigate(`/scoring/${companyId}/product-health`);
    }
  };

  const getMetrics = (): MetricDisplay[] => {
    if (!metrics) {
      return [
        { label: 'Uptime', value: '--', status: 'neutral' },
        { label: 'Avg Response', value: '--', status: 'neutral' },
        { label: 'Error Rate', value: '--', status: 'neutral' },
        { label: 'Deploy Freq', value: '--', status: 'neutral' },
        { label: 'Tech Debt', value: '--', status: 'neutral' },
        { label: 'Test Coverage', value: '--', status: 'neutral' },
      ];
    }

    const m = metrics.metrics;

    const getUptimeStatus = (val: number): 'good' | 'warning' | 'bad' => {
      if (val >= 99.9) return 'good';
      if (val >= 99) return 'warning';
      return 'bad';
    };

    const getResponseStatus = (val: number): 'good' | 'warning' | 'bad' => {
      if (val <= 200) return 'good';
      if (val <= 500) return 'warning';
      return 'bad';
    };

    const getErrorStatus = (val: number): 'good' | 'warning' | 'bad' => {
      if (val <= 0.5) return 'good';
      if (val <= 2) return 'warning';
      return 'bad';
    };

    return [
      {
        label: 'Uptime',
        value: m.UptimePct?.current_value.numeric ? `${m.UptimePct.current_value.numeric}%` : '--',
        status: m.UptimePct?.current_value.numeric ? getUptimeStatus(m.UptimePct.current_value.numeric) : 'neutral'
      },
      {
        label: 'Avg Response',
        value: m.AvgResponseTimeMs?.current_value.numeric ? `${m.AvgResponseTimeMs.current_value.numeric}ms` : '--',
        status: m.AvgResponseTimeMs?.current_value.numeric ? getResponseStatus(m.AvgResponseTimeMs.current_value.numeric) : 'neutral'
      },
      {
        label: 'Error Rate',
        value: m.ErrorRatePct?.current_value.numeric ? `${m.ErrorRatePct.current_value.numeric}%` : '--',
        status: m.ErrorRatePct?.current_value.numeric ? getErrorStatus(m.ErrorRatePct.current_value.numeric) : 'neutral'
      },
      {
        label: 'Deploy Freq',
        value: m.DeployFrequency?.current_value.numeric ? `${m.DeployFrequency.current_value.numeric}/day` : '--',
        status: 'neutral'
      },
      {
        label: 'Tech Debt',
        value: m.TechDebtLevel?.current_value.text ?? '--',
        status: m.TechDebtLevel?.current_value.text === 'Low' ? 'good' :
          m.TechDebtLevel?.current_value.text === 'Medium' ? 'warning' :
          m.TechDebtLevel?.current_value.text === 'High' ? 'bad' : 'neutral'
      },
      {
        label: 'Test Coverage',
        value: m.TestCoveragePct?.current_value.numeric ? `${m.TestCoveragePct.current_value.numeric}%` : '--',
        status: m.TestCoveragePct?.current_value.numeric
          ? (m.TestCoveragePct.current_value.numeric >= 70 ? 'good' :
             m.TestCoveragePct.current_value.numeric >= 40 ? 'warning' : 'bad')
          : 'neutral'
      },
    ];
  };

  const displayMetrics = getMetrics();

  return (
    <div className={styles.container} onClick={handleClick}>
      <div className={styles.header}>
        <h3 className={styles.title}>Product Health</h3>
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
