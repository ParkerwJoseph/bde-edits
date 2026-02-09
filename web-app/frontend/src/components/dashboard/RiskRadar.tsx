import { useNavigate } from 'react-router-dom';
import styles from '../../styles/components/dashboard/RiskRadar.module.css';
import type { FlagsResponse } from '../../api/scoringApi';

interface RiskRadarProps {
  flags: FlagsResponse | null;
  companyId: string | null;
  onClick?: () => void;
}

export default function RiskRadar({ flags, companyId, onClick }: RiskRadarProps) {
  const navigate = useNavigate();
  const isPlaceholder = !flags;

  const redCount = flags?.red_flags.length ?? 0;
  const yellowCount = flags?.yellow_flags.length ?? 0;
  const greenCount = flags?.green_accelerants.length ?? 0;

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (companyId) {
      navigate(`/scoring/${companyId}/risks`);
    }
  };

  // Get top flags for preview
  const topRedFlags = flags?.red_flags.slice(0, 2) ?? [];
  const topYellowFlags = flags?.yellow_flags.slice(0, 2) ?? [];

  return (
    <div className={styles.container} onClick={handleClick}>
      <div className={styles.header}>
        <h3 className={styles.title}>Risk Radar</h3>
        <div className={styles.badges}>
          <span className={`${styles.badge} ${styles.redBadge}`}>
            {isPlaceholder ? '-' : redCount}
          </span>
          <span className={`${styles.badge} ${styles.yellowBadge}`}>
            {isPlaceholder ? '-' : yellowCount}
          </span>
          <span className={`${styles.badge} ${styles.greenBadge}`}>
            {isPlaceholder ? '-' : greenCount}
          </span>
        </div>
      </div>

      <div className={styles.flagsList}>
        {isPlaceholder ? (
          <>
            <div className={`${styles.flagItem} ${styles.placeholder}`}>
              <div className={styles.flagDot} />
              <span className={styles.flagText}>No data available</span>
            </div>
            <div className={`${styles.flagItem} ${styles.placeholder}`}>
              <div className={styles.flagDot} />
              <span className={styles.flagText}>Run scoring to see flags</span>
            </div>
          </>
        ) : (
          <>
            {topRedFlags.map((flag, idx) => (
              <div key={`red-${idx}`} className={`${styles.flagItem} ${styles.redFlag}`}>
                <div className={`${styles.flagDot} ${styles.redDot}`} />
                <span className={styles.flagText}>{flag.text}</span>
              </div>
            ))}
            {topYellowFlags.map((flag, idx) => (
              <div key={`yellow-${idx}`} className={`${styles.flagItem} ${styles.yellowFlag}`}>
                <div className={`${styles.flagDot} ${styles.yellowDot}`} />
                <span className={styles.flagText}>{flag.text}</span>
              </div>
            ))}
            {topRedFlags.length === 0 && topYellowFlags.length === 0 && (
              <>
                {flags?.green_accelerants.slice(0, 2).map((flag, idx) => (
                  <div key={`green-${idx}`} className={`${styles.flagItem} ${styles.greenFlag}`}>
                    <div className={`${styles.flagDot} ${styles.greenDot}`} />
                    <span className={styles.flagText}>{flag.text}</span>
                  </div>
                ))}
              </>
            )}
          </>
        )}
      </div>

      <span className={styles.viewMore}>View All Flags &rarr;</span>
    </div>
  );
}
