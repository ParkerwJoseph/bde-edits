/**
 * TodaysPriorities Component
 *
 * Displays priority items that need attention today.
 * Shows urgency level, category, and quick action buttons.
 */

import { ArrowRight, AlertTriangle, TrendingDown, Calendar, Info } from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/home/TodaysPriorities.module.css';

type Urgency = 'critical' | 'warning' | 'info';
type Category = 'financial' | 'customer' | 'gtm' | 'ecosystem';

interface Priority {
  id: string;
  title: string;
  category: Category;
  urgency: Urgency;
  action: string;
  metric?: string;
}

export interface TodaysPrioritiesProps {
  /** Custom priorities data */
  priorities?: Priority[];
  /** Callback when priority action is clicked */
  onActionClick?: (priority: Priority) => void;
}

// Empty array - no fake default data
const EMPTY_PRIORITIES: Priority[] = [];

const urgencyIcons = {
  critical: AlertTriangle,
  warning: TrendingDown,
  info: Calendar,
};

const categoryStyles: Record<Category, string> = {
  financial: styles.categoryFinancial,
  customer: styles.categoryCustomer,
  gtm: styles.categoryGtm,
  ecosystem: styles.categoryEcosystem,
};

export function TodaysPriorities({
  priorities = EMPTY_PRIORITIES,
  onActionClick,
}: TodaysPrioritiesProps) {
  const isEmpty = priorities.length === 0;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h3 className={styles.title}>Today's Priorities</h3>
        {!isEmpty && <span className={styles.count}>{priorities.length} items</span>}
      </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className={styles.emptyState}>
          <Info size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No priorities yet</p>
          <p className={styles.emptySubtext}>Priorities will appear based on your data</p>
        </div>
      ) : (
        /* Priority List */
        <div className={styles.list}>
          {priorities.map((priority, index) => {
            const Icon = urgencyIcons[priority.urgency];

            return (
              <div
                key={priority.id}
                className={styles.item}
                style={{ animationDelay: `${index * 60}ms` }}
              >
                <div className={cn(styles.iconWrapper, categoryStyles[priority.category])}>
                  <Icon size={14} />
                </div>

                <div className={styles.content}>
                  <p className={styles.itemTitle}>{priority.title}</p>
                </div>

                <button
                  className={styles.actionButton}
                  onClick={() => onActionClick?.(priority)}
                >
                  {priority.action}
                  <ArrowRight size={12} />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default TodaysPriorities;
