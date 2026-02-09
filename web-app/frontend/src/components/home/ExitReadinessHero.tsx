/**
 * ExitReadinessHero Component
 *
 * Main hero section showing exit readiness score with animated ring gauge.
 * Displays confidence score, status label, and summary text.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Info } from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/Tooltip';
import styles from '../../styles/components/home/ExitReadinessHero.module.css';

type ReadinessStatus = 'ready' | 'conditional' | 'not-ready';

export interface ExitReadinessHeroProps {
  /** Readiness status */
  status?: ReadinessStatus;
  /** Headline text */
  headline?: string;
  /** Summary description */
  summary?: string;
  /** Confidence score (0-100) */
  confidenceScore?: number;
  /** Whether to hide score factors */
  hideScoreFactors?: boolean;
  /** Custom click handler */
  onClick?: () => void;
}

// Color configuration based on score
const getScoreConfig = (score: number) => {
  if (score >= 71) {
    const intensity = (score - 71) / 28;
    return {
      label: 'Exit Ready',
      color: `hsl(152, ${55 + intensity * 15}%, ${50 - intensity * 10}%)`,
      glowColor: `rgba(34, 197, 94, ${0.3 + intensity * 0.2})`,
    };
  } else if (score >= 31) {
    const intensity = (score - 31) / 39;
    return {
      label: 'Conditional',
      color: `hsl(${50 - intensity * 10}, ${85 + intensity * 10}%, ${55 - intensity * 10}%)`,
      glowColor: `rgba(245, 158, 11, ${0.3 + intensity * 0.2})`,
    };
  } else {
    const intensity = Math.max(0, (score - 10) / 20);
    return {
      label: 'Not Ready',
      color: `hsl(0, ${70 + intensity * 15}%, ${58 - intensity * 10}%)`,
      glowColor: `rgba(239, 68, 68, ${0.3 + intensity * 0.2})`,
    };
  }
};

export function ExitReadinessHero({
  summary = 'Revenue quality is strong. Customer concentration (42% from top client) and founder-led sales create transition risk that buyers will price into the deal.',
  confidenceScore = 72,
  onClick,
}: ExitReadinessHeroProps) {
  const navigate = useNavigate();
  const config = getScoreConfig(confidenceScore);
  const [animatedScore, setAnimatedScore] = useState(0);

  // Ring dimensions
  const size = 120;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const scorePercentage = confidenceScore / 100;
  const dashOffset = circumference * (1 - scorePercentage);

  // Animate score on mount
  useEffect(() => {
    const duration = 600;
    const steps = 20;
    const increment = confidenceScore / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= confidenceScore) {
        setAnimatedScore(confidenceScore);
        clearInterval(timer);
      } else {
        setAnimatedScore(Math.floor(current));
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [confidenceScore]);

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      navigate('/metrics/exit-hero');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleClick();
    }
  };

  return (
    <div
      className={styles.container}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      {/* Top accent line */}
      <div
        className={styles.accentLine}
        style={{ background: `linear-gradient(90deg, ${config.color}, transparent 60%)` }}
      />

      {/* Main container */}
      <div className={styles.content}>
        <div className={styles.layout}>
          {/* Left: Score Ring */}
          <div className={styles.ringSection}>
            <div className={styles.ringContainer}>
              <svg
                width={size}
                height={size}
                className={styles.ring}
                style={{ filter: `drop-shadow(0 0 12px ${config.glowColor})` }}
              >
                {/* Background circle */}
                <circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  fill="none"
                  stroke="var(--border-default)"
                  strokeWidth={strokeWidth}
                />
                {/* Score circle */}
                <circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  fill="none"
                  stroke={config.color}
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={dashOffset}
                  className={styles.ringProgress}
                />
              </svg>

              {/* Center content */}
              <div className={styles.ringCenter}>
                <span
                  className={styles.scoreValue}
                  style={{ color: config.color }}
                >
                  {animatedScore}
                </span>
              </div>
            </div>

            {/* Status badge below ring */}
            <div className={styles.statusBadge}>
              <div
                className={styles.statusDot}
                style={{ backgroundColor: config.color }}
              />
              <span
                className={styles.statusLabel}
                style={{ color: config.color }}
              >
                {config.label}
              </span>
            </div>
          </div>

          {/* Center: Title and Description */}
          <div className={styles.textSection}>
            <div className={styles.titleRow}>
              <h2 className={styles.sectionTitle}>Exit Readiness</h2>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button className={styles.infoButton}>
                      <Info size={12} />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top">
                    Composite score based on 8 pillars of exit readiness assessment
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>

            <p className={styles.summary}>{summary}</p>

            {/* View details link */}
            <div className={styles.viewDetails}>
              <span>View details</span>
              <ChevronRight size={14} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExitReadinessHero;
