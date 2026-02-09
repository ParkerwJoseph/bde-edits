import { useNavigate } from 'react-router-dom';
import styles from '../../styles/components/dashboard/PillarScoreBar.module.css';
import { PILLAR_CONFIG, getHealthStatusColor } from '../../api/scoringApi';
import type { BDEPillar, PillarScore } from '../../api/scoringApi';

interface PillarScoreBarProps {
  pillarScores: Record<BDEPillar, PillarScore> | null;
  companyId: string | null;
  onClick?: () => void;
  enablePillarClick?: boolean; // Enable individual pillar navigation
}

const PILLAR_ORDER: BDEPillar[] = [
  'financial_health',
  'gtm_engine',
  'customer_health',
  'product_technical',
  'operational_maturity',
  'leadership_transition',
  'ecosystem_dependency',
  'service_software_ratio',
];

export default function PillarScoreBar({ pillarScores, companyId, onClick, enablePillarClick = false }: PillarScoreBarProps) {
  const navigate = useNavigate();
  const isPlaceholder = !pillarScores;

  const handleContainerClick = () => {
    if (onClick) {
      onClick();
    } else if (companyId) {
      navigate(`/scoring/${companyId}/pillar-scores`);
    }
  };

  const handlePillarClick = (pillar: BDEPillar, e: React.MouseEvent) => {
    if (!enablePillarClick) return;

    e.stopPropagation();
    if (companyId) {
      navigate(`/scoring/${companyId}/pillars/${pillar}`);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header} onClick={handleContainerClick} style={{ cursor: 'pointer' }}>
        <h3 className={styles.title}>Pillar Scores</h3>
        <span className={styles.viewMore}>View Details &rarr;</span>
      </div>

      <div className={styles.pillarsGrid}>
        {PILLAR_ORDER.map((pillar) => {
          const config = PILLAR_CONFIG[pillar];
          const score = pillarScores?.[pillar];
          const scoreValue = score?.score ?? 0;
          const normalizedScore = (scoreValue / 5) * 100;

          return (
            <div
              key={pillar}
              className={styles.pillarRow}
              onClick={(e) => handlePillarClick(pillar, e)}
              style={{ cursor: enablePillarClick ? 'pointer' : 'default' }}
            >
              <div className={styles.pillarInfo}>
                <span className={styles.pillarName}>{config.label}</span>
                <span className={styles.pillarWeight}>{(config.weight * 100).toFixed(0)}%</span>
              </div>

              <div className={styles.barContainer}>
                <div className={styles.barBackground}>
                  {!isPlaceholder && (
                    <div
                      className={styles.barFill}
                      style={{
                        width: `${normalizedScore}%`,
                        backgroundColor: score ? getHealthStatusColor(score.health_status) : config.color
                      }}
                    />
                  )}
                </div>
                <span className={styles.scoreValue}>
                  {isPlaceholder ? '--' : scoreValue.toFixed(1)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
