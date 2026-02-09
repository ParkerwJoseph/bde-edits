/**
 * ValueFragilityMatrix Component
 *
 * Signal Map visualization showing value vs fragility for different business signals.
 * Displays signals on a 2D matrix with value on Y-axis and fragility on X-axis.
 */

import { useState } from 'react';
import { Info } from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/Tooltip';
import styles from '../../styles/components/analytics/ValueFragilityMatrix.module.css';

export interface Signal {
  id: string;
  name: string;
  value: number; // 0-100, higher = more valuable
  fragility: number; // 0-100, higher = more fragile/risky
  category: 'revenue' | 'customer' | 'product' | 'team' | 'operations';
  description?: string;
}

export interface ValueFragilityMatrixProps {
  /** Signals to display on the matrix */
  signals?: Signal[];
  /** Title of the matrix */
  title?: string;
  /** Whether to show the legend */
  showLegend?: boolean;
  /** Callback when a signal is clicked */
  onSignalClick?: (signal: Signal) => void;
  /** Additional class name */
  className?: string;
}

// Empty array - no fake default data
const EMPTY_SIGNALS: Signal[] = [];

const CATEGORY_COLORS: Record<Signal['category'], string> = {
  revenue: 'var(--score-green)',
  customer: 'var(--score-blue, #3b82f6)',
  product: 'var(--score-purple, #8b5cf6)',
  team: 'var(--score-yellow)',
  operations: 'var(--score-orange, #f97316)',
};

const CATEGORY_LABELS: Record<Signal['category'], string> = {
  revenue: 'Revenue',
  customer: 'Customer',
  product: 'Product',
  team: 'Team',
  operations: 'Operations',
};

export function ValueFragilityMatrix({
  signals = EMPTY_SIGNALS,
  title = 'Signal Map',
  showLegend = true,
  onSignalClick,
  className,
}: ValueFragilityMatrixProps) {
  const [hoveredSignal, setHoveredSignal] = useState<string | null>(null);
  const isEmpty = signals.length === 0;

  // Get unique categories from signals
  const categories = [...new Set(signals.map(s => s.category))];

  return (
    <div className={cn(styles.container, className)}>
      {/* Header */}
      <div className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className={styles.infoButton}>
                <Info size={16} />
              </button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Signals in the upper-left quadrant are high-value and low-risk.</p>
              <p>Signals in the lower-right are high-risk areas to address.</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className={styles.emptyState}>
          <Info size={32} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No signals available</p>
          <p className={styles.emptySubtext}>Upload documents to map business signals</p>
        </div>
      ) : (
        <>
          {/* Matrix */}
          <div className={styles.matrixWrapper}>
            {/* Y-Axis Label */}
            <div className={styles.yAxisLabel}>
              <span>Value</span>
            </div>

            {/* Matrix Grid */}
            <div className={styles.matrix}>
              {/* Grid lines and quadrant backgrounds */}
              <div className={styles.gridBackground}>
                <div className={cn(styles.quadrant, styles.quadrantTopLeft)} />
                <div className={cn(styles.quadrant, styles.quadrantTopRight)} />
                <div className={cn(styles.quadrant, styles.quadrantBottomLeft)} />
                <div className={cn(styles.quadrant, styles.quadrantBottomRight)} />
              </div>

              {/* Quadrant labels */}
              <div className={styles.quadrantLabels}>
                <span className={cn(styles.quadrantLabel, styles.labelTopLeft)}>Strengths</span>
                <span className={cn(styles.quadrantLabel, styles.labelTopRight)}>Watch</span>
                <span className={cn(styles.quadrantLabel, styles.labelBottomLeft)}>Low Priority</span>
                <span className={cn(styles.quadrantLabel, styles.labelBottomRight)}>Address</span>
              </div>

              {/* Signals */}
              {signals.map(signal => (
                <TooltipProvider key={signal.id}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        className={cn(
                          styles.signal,
                          hoveredSignal === signal.id && styles.signalHovered
                        )}
                        style={{
                          left: `${signal.fragility}%`,
                          bottom: `${signal.value}%`,
                          backgroundColor: CATEGORY_COLORS[signal.category],
                        }}
                        onClick={() => onSignalClick?.(signal)}
                        onMouseEnter={() => setHoveredSignal(signal.id)}
                        onMouseLeave={() => setHoveredSignal(null)}
                        aria-label={signal.name}
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className={styles.tooltipContent}>
                        <strong>{signal.name}</strong>
                        {signal.description && <p>{signal.description}</p>}
                        <p>Value: {signal.value}% | Fragility: {signal.fragility}%</p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ))}
            </div>

            {/* X-Axis Label */}
            <div className={styles.xAxisLabel}>
              <span>Fragility</span>
            </div>
          </div>

          {/* Legend */}
          {showLegend && categories.length > 0 && (
            <div className={styles.legend}>
              {categories.map(category => (
                <div key={category} className={styles.legendItem}>
                  <span
                    className={styles.legendDot}
                    style={{ backgroundColor: CATEGORY_COLORS[category] }}
                  />
                  <span className={styles.legendLabel}>{CATEGORY_LABELS[category]}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ValueFragilityMatrix;
