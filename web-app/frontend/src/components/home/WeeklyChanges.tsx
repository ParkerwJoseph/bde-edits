/**
 * WeeklyChanges Component
 *
 * Displays metrics that have changed during the week.
 * Shows trend direction, percentage change, and whether the change is positive.
 */

import { ArrowUpRight, ArrowDownRight, Minus, Info } from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/home/WeeklyChanges.module.css';

type Trend = 'up' | 'down' | 'neutral';

interface Change {
  id: string;
  metric: string;
  acronym?: string;
  previousValue: string;
  currentValue: string;
  change: number;
  trend: Trend;
  isPositive: boolean;
  category: string;
}

export interface WeeklyChangesProps {
  /** Custom changes data */
  changes?: Change[];
  /** Number of items to show initially */
  initialCount?: number;
  /** Callback when "more" is clicked */
  onViewMore?: () => void;
}

// Empty array - no fake default data
const EMPTY_CHANGES: Change[] = [];

const trendIcons = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  neutral: Minus,
};

export function WeeklyChanges({
  changes = EMPTY_CHANGES,
  initialCount = 3,
  onViewMore,
}: WeeklyChangesProps) {
  const visibleChanges = changes.slice(0, initialCount);
  const remainingCount = changes.length - initialCount;
  const isEmpty = changes.length === 0;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h3 className={styles.title}>What's Changed This Week</h3>
        {remainingCount > 0 && (
          <button className={styles.moreButton} onClick={onViewMore}>
            +{remainingCount} more
          </button>
        )}
      </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className={styles.emptyState}>
          <Info size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No changes this week</p>
          <p className={styles.emptySubtext}>Changes will appear as data is analyzed</p>
        </div>
      ) : (
        /* Changes List */
        <div className={styles.list}>
          {visibleChanges.map((change, index) => {
            const TrendIcon = trendIcons[change.trend];
            const trendClass = change.isPositive ? styles.trendPositive : styles.trendNegative;

            return (
              <div
                key={change.id}
                className={styles.item}
                style={{ animationDelay: `${index * 60}ms` }}
              >
                <div className={cn(styles.trendIcon, trendClass)}>
                  <TrendIcon size={16} />
                </div>

                <div className={styles.content}>
                  <div className={styles.metricRow}>
                    {change.acronym && (
                      <span className={styles.acronym}>{change.acronym}</span>
                    )}
                    <span className={styles.category}>{change.category}</span>
                  </div>
                  <p className={styles.values}>
                    {change.previousValue} → {change.currentValue}
                  </p>
                </div>

                <div className={cn(styles.changeValue, trendClass)}>
                  {change.change > 0 ? '+' : ''}
                  {change.change.toFixed(1)}%
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default WeeklyChanges;
