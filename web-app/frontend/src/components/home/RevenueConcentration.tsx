/**
 * RevenueConcentration Component
 *
 * Horizontal stacked bar chart showing revenue concentration by customer tiers:
 * - Top 1 Customer
 * - Top 2-5 Customers
 * - Remaining Customers
 */

import { useNavigate } from 'react-router-dom';
import { ChevronRight, Info } from 'lucide-react';
import styles from '../../styles/components/home/RevenueConcentration.module.css';

export interface ConcentrationTier {
  label: string;
  percentage: number;
  color: 'high' | 'medium' | 'low';
}

export interface RevenueConcentrationProps {
  /** Optional class name */
  className?: string;
  /** Concentration data - Top 1, Top 2-5, Remaining percentages */
  concentrationData?: {
    top1Pct: number;      // Top 1 customer percentage
    top2to5Pct: number;   // Top 2-5 customers combined percentage
    remainingPct: number; // Remaining customers percentage
  };
}

export function RevenueConcentration({ className, concentrationData }: RevenueConcentrationProps) {
  const navigate = useNavigate();
  const isEmpty = !concentrationData ||
    (concentrationData.top1Pct === 0 && concentrationData.top2to5Pct === 0 && concentrationData.remainingPct === 0);

  const handleClick = () => {
    navigate('/metrics/revenue-concentration');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      navigate('/metrics/revenue-concentration');
    }
  };

  // Calculate tier data for display
  const tiers: ConcentrationTier[] = concentrationData ? [
    {
      label: 'Top 1 Customer',
      percentage: concentrationData.top1Pct,
      color: concentrationData.top1Pct > 25 ? 'high' : concentrationData.top1Pct > 15 ? 'medium' : 'low',
    },
    {
      label: 'Top 2-5 Customers',
      percentage: concentrationData.top2to5Pct,
      color: 'medium',
    },
    {
      label: 'Remaining',
      percentage: concentrationData.remainingPct,
      color: 'low',
    },
  ] : [];

  // Get color class based on risk level
  const getColorClass = (color: 'high' | 'medium' | 'low') => {
    switch (color) {
      case 'high':
        return styles.barHigh;    // Red/orange - high concentration risk
      case 'medium':
        return styles.barMedium;  // Yellow/amber - moderate
      case 'low':
        return styles.barLow;     // Green - healthy diversification
      default:
        return styles.barMedium;
    }
  };

  return (
    <div
      className={`${styles.container} ${className || ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.title}>Revenue Concentration</span>
        {!isEmpty && <ChevronRight className={styles.chevron} size={16} />}
      </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className={styles.emptyState}>
          <Info size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No revenue data available</p>
          <p className={styles.emptySubtext}>Upload financial documents to see concentration</p>
        </div>
      ) : (
        <>
          {/* Stacked horizontal bar - single bar with all tiers */}
          <div className={styles.barsContainer}>
            {tiers.map((tier) => (
              <div key={tier.label} className={styles.barRow}>
                <span className={styles.clientName}>{tier.label}</span>
                <div className={styles.barTrack}>
                  <div
                    className={`${styles.barFill} ${getColorClass(tier.color)}`}
                    style={{ width: `${tier.percentage}%` }}
                  />
                </div>
                <span className={styles.percentage}>{tier.percentage.toFixed(0)}%</span>
              </div>
            ))}
          </div>

          {/* Legend */}
          <div className={styles.legend}>
            <div className={styles.legendItem}>
              <div className={styles.legendDotHigh} />
              <span>High Risk (&gt;25%)</span>
            </div>
            <div className={styles.legendItem}>
              <div className={styles.legendDotMedium} />
              <span>Moderate</span>
            </div>
            <div className={styles.legendItem}>
              <div className={styles.legendDotLow} />
              <span>Healthy</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default RevenueConcentration;
