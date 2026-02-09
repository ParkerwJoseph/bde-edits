import styles from '../../styles/components/dashboard/ScoreGauge.module.css';
import { getScoreRating } from '../../api/scoringApi';

interface ScoreGaugeProps {
  score: number | null;
  label?: string;
  subtitle?: string;
  size?: 'small' | 'medium' | 'large';
  onClick?: () => void;
}

export default function ScoreGauge({
  score,
  label = 'Business Health',
  subtitle,
  size = 'large',
  onClick
}: ScoreGaugeProps) {
  const isPlaceholder = score === null;
  const displayScore = score ?? 0;
  const rating = getScoreRating(displayScore);

  // Calculate arc parameters
  const radius = size === 'large' ? 80 : size === 'medium' ? 60 : 40;
  const strokeWidth = size === 'large' ? 12 : size === 'medium' ? 10 : 8;
  const circumference = Math.PI * radius;
  const progress = (displayScore / 100) * circumference;

  const sizeClass = styles[size];

  return (
    <div
      className={`${styles.container} ${sizeClass} ${onClick ? styles.clickable : ''}`}
      onClick={onClick}
    >
      <div className={styles.gaugeWrapper}>
        <svg
          className={styles.gauge}
          viewBox={`0 0 ${(radius + strokeWidth) * 2} ${radius + strokeWidth + 10}`}
        >
          {/* Background arc */}
          <path
            className={styles.backgroundArc}
            d={`M ${strokeWidth} ${radius + strokeWidth} A ${radius} ${radius} 0 0 1 ${radius * 2 + strokeWidth} ${radius + strokeWidth}`}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Progress arc */}
          {!isPlaceholder && (
            <path
              className={styles.progressArc}
              d={`M ${strokeWidth} ${radius + strokeWidth} A ${radius} ${radius} 0 0 1 ${radius * 2 + strokeWidth} ${radius + strokeWidth}`}
              fill="none"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={`${progress} ${circumference}`}
              style={{ stroke: rating.color }}
            />
          )}
        </svg>

        <div className={styles.scoreDisplay}>
          {isPlaceholder ? (
            <span className={styles.placeholder}>--</span>
          ) : (
            <>
              <span className={styles.scoreValue}>{displayScore}</span>
              <span className={styles.scoreMax}>/100</span>
            </>
          )}
        </div>
      </div>

      <div className={styles.labelContainer}>
        {!isPlaceholder && (
          <span
            className={styles.ratingBadge}
            style={{ backgroundColor: `${rating.color}20`, color: rating.color }}
          >
            {rating.label}
          </span>
        )}
        <span className={styles.label}>{label}</span>
        {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
      </div>
    </div>
  );
}
