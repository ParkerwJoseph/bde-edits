/**
 * PillarScorecard Component
 *
 * Grid of pillar cards showing name, score, trend, and confidence.
 * Used on the Analytics page for the 8-Pillar Scorecard section.
 */

import { useNavigate } from 'react-router-dom';
import {
  DollarSign,
  Target,
  Users,
  Cpu,
  Settings,
  Crown,
  Network,
  ArrowRightLeft,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  Info,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import { type BDEPillar, type HealthStatus, PILLAR_CONFIG } from '../../api/scoringApi';
import styles from '../../styles/components/analytics/PillarScorecard.module.css';

// Map pillar IDs to icons
const PILLAR_ICONS: Record<BDEPillar, LucideIcon> = {
  financial_health: DollarSign,
  gtm_engine: Target,
  customer_health: Users,
  product_technical: Cpu,
  operational_maturity: Settings,
  leadership_transition: Crown,
  ecosystem_dependency: Network,
  service_software_ratio: ArrowRightLeft,
};

// Short names for display
const PILLAR_SHORT_NAMES: Record<BDEPillar, string> = {
  financial_health: 'Financial',
  gtm_engine: 'GTM',
  customer_health: 'Customer',
  product_technical: 'Product',
  operational_maturity: 'Operations',
  leadership_transition: 'Leadership',
  ecosystem_dependency: 'Ecosystem',
  service_software_ratio: 'Svc/Software',
};

// Pillar colors
const PILLAR_COLORS: Record<BDEPillar, string> = {
  financial_health: styles.colorFinancial,
  gtm_engine: styles.colorGtm,
  customer_health: styles.colorCustomer,
  product_technical: styles.colorProduct,
  operational_maturity: styles.colorOperations,
  leadership_transition: styles.colorLeadership,
  ecosystem_dependency: styles.colorEcosystem,
  service_software_ratio: styles.colorService,
};

export interface PillarScore {
  score: number;
  health_status: HealthStatus;
  confidence: number;
  data_coverage: number;
  trend?: 'up' | 'down' | 'flat';
}

export interface PillarScorecardProps {
  /** Pillar scores data */
  pillarScores?: Record<BDEPillar, PillarScore>;
  /** Callback when pillar is clicked */
  onPillarClick?: (pillarId: string) => void;
}

// Empty pillar score for when no data is available
const EMPTY_PILLAR_SCORE: PillarScore = {
  score: 0,
  health_status: 'red', // Will be overridden to show empty state
  confidence: 0,
  data_coverage: 0,
  trend: undefined,
};

function getScoreColorClass(score: number): string {
  if (score >= 4.0) return styles.scoreStrong;
  if (score >= 2.5) return styles.scoreAtRisk;
  return styles.scoreHighRisk;
}

export function PillarScorecard({
  pillarScores,
  onPillarClick,
}: PillarScorecardProps) {
  const navigate = useNavigate();
  const isEmpty = !pillarScores || Object.keys(pillarScores).length === 0;

  const handleClick = (pillarId: string) => {
    if (onPillarClick) {
      onPillarClick(pillarId);
    } else {
      navigate(`/analytics/pillar/${pillarId}`);
    }
  };

  const pillarIds = Object.keys(PILLAR_CONFIG) as BDEPillar[];

  // Show empty state if no data
  if (isEmpty) {
    return (
      <div className={styles.emptyState}>
        <Info size={32} className={styles.emptyIcon} />
        <p className={styles.emptyText}>No pillar scores available</p>
        <p className={styles.emptySubtext}>Upload documents to analyze your pillars</p>
      </div>
    );
  }

  return (
    <div className={styles.grid}>
      {pillarIds.map((pillarId) => {
        const Icon = PILLAR_ICONS[pillarId];
        const scores = pillarScores[pillarId] || EMPTY_PILLAR_SCORE;
        const shortName = PILLAR_SHORT_NAMES[pillarId];
        const colorClass = PILLAR_COLORS[pillarId];
        const hasScore = scores.score > 0;
        const displayScore = hasScore ? scores.score.toFixed(1) : '—'; // Score is already 0-5 scale

        return (
          <button
            key={pillarId}
            onClick={() => handleClick(pillarId)}
            className={cn(styles.card, !hasScore && styles.cardEmpty)}
          >
            <div className={styles.cardHeader}>
              <div className={cn(styles.iconWrapper, hasScore ? colorClass : styles.iconWrapperEmpty)}>
                <Icon size={16} />
              </div>
              <ChevronRight size={16} className={styles.chevron} />
            </div>

            <p className={styles.pillarName}>{shortName}</p>

            <div className={styles.scoreRow}>
              <span className={cn(styles.score, hasScore ? getScoreColorClass(scores.score) : styles.scoreEmpty)}>
                {displayScore}
              </span>
              {hasScore && (
                <div className={styles.trendIcon}>
                  {scores.trend === 'up' && <TrendingUp size={12} className={styles.trendUp} />}
                  {scores.trend === 'down' && <TrendingDown size={12} className={styles.trendDown} />}
                  {scores.trend === 'flat' && <Minus size={12} className={styles.trendFlat} />}
                </div>
              )}
            </div>

            <div className={styles.confidenceSection}>
              <div className={styles.confidenceBar}>
                <div
                  className={styles.confidenceFill}
                  style={{ width: `${scores.confidence}%` }}
                />
              </div>
              <p className={styles.confidenceText}>
                {hasScore ? `${scores.confidence}% conf` : 'No data'}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

export default PillarScorecard;
