import styles from '../../styles/components/dashboard/DataCoverage.module.css';
import { PILLAR_CONFIG } from '../../api/scoringApi';
import type { BDEPillar, PillarScore } from '../../api/scoringApi';

interface DataCoverageProps {
  pillarScores: Record<BDEPillar, PillarScore> | null;
}

const PILLAR_ORDER: BDEPillar[] = [
  'financial_health',
  'gtm_engine',
  'customer_health',
  'product_technical',
  'operational_maturity',
];

export default function DataCoverage({ pillarScores }: DataCoverageProps) {
  const isPlaceholder = !pillarScores;

  // Calculate average coverage
  const avgCoverage = pillarScores
    ? Object.values(pillarScores).reduce((sum, p) => sum + (p.data_coverage || 0), 0) /
      Object.values(pillarScores).length
    : 0;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <h3 className={styles.title}>Data Coverage</h3>
          <span className={styles.avgBadge}>
            {isPlaceholder ? '--' : `${Math.round(avgCoverage)}%`}
          </span>
        </div>
        <span className={styles.subtitle}>Evidence quality per pillar</span>
      </div>

      <div className={styles.coverageList}>
        {PILLAR_ORDER.map((pillar) => {
          const config = PILLAR_CONFIG[pillar];
          const score = pillarScores?.[pillar];
          const coverage = score?.data_coverage ?? 0;

          return (
            <div key={pillar} className={styles.coverageRow}>
              <div className={styles.rowHeader}>
                <span className={styles.pillarName}>{config.label}</span>
                <span className={styles.coverageValue}>
                  {isPlaceholder ? '--' : `${coverage}%`}
                </span>
              </div>
              <div className={styles.barBackground}>
                {!isPlaceholder && (
                  <div
                    className={styles.barFill}
                    style={{
                      width: `${coverage}%`,
                      backgroundColor: coverage >= 70 ? '#22c55e' : coverage >= 40 ? '#f59e0b' : '#ef4444'
                    }}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={`${styles.legendDot} ${styles.high}`} />
          High (&gt;70%)
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.legendDot} ${styles.medium}`} />
          Medium (40-70%)
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.legendDot} ${styles.low}`} />
          Low (&lt;40%)
        </span>
      </div>
    </div>
  );
}
