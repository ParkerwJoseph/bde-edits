/**
 * MultipleImprovers Component
 *
 * Displays actions that can improve valuation multiple.
 * Shows priority, impact label, status, effort, and progress.
 */

import { useNavigate } from 'react-router-dom';
import { ChevronRight, Info } from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/Tooltip';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/home/MultipleImprovers.module.css';

type Level = 'high' | 'medium' | 'low' | null;
type Status = 'critical' | 'warning' | 'good';

interface MultipleImprover {
  id: string;
  action: string;
  impactLabel: string;
  progress: { current: number; total: number };
  status: Status;
  categories: {
    impact: Level;
    effort: Level;
    priority: number | null;
  };
}

export interface MultipleImproversProps {
  /** Custom improvers data */
  improvers?: MultipleImprover[];
  /** Callback when improver is clicked */
  onImproverClick?: (improverId: string) => void;
  /** Callback for view all */
  onViewAll?: () => void;
}

// Empty array - no fake default data
const EMPTY_IMPROVERS: MultipleImprover[] = [];

const statusConfig: Record<Status, { color: string; className: string; label: string }> = {
  critical: {
    color: 'hsl(var(--kpi-high-risk))',
    className: styles.statusCritical,
    label: 'At Risk',
  },
  warning: {
    color: 'hsl(var(--kpi-watch))',
    className: styles.statusWarning,
    label: 'In Progress',
  },
  good: {
    color: 'hsl(var(--kpi-strong))',
    className: styles.statusGood,
    label: 'On Track',
  },
};

// Level Badge Component
function LevelBadge({
  level,
  variant = 'default',
}: {
  level: Level;
  variant?: 'default' | 'effort';
}) {
  if (!level) return <span className={styles.levelEmpty}>-</span>;

  const label = level === 'high' ? 'High' : level === 'medium' ? 'Med' : 'Low';

  const colorClass =
    variant === 'effort'
      ? level === 'high'
        ? styles.levelEffortHigh
        : level === 'medium'
          ? styles.levelEffortMed
          : styles.levelEffortLow
      : level === 'high'
        ? styles.levelImpactHigh
        : level === 'medium'
          ? styles.levelImpactMed
          : styles.levelImpactLow;

  return <span className={cn(styles.levelBadge, colorClass)}>{label}</span>;
}

// Priority Badge Component
function PriorityBadge({ priority }: { priority: number | null }) {
  if (!priority) return <span className={styles.levelEmpty}>-</span>;
  return <span className={styles.priorityBadge}>{priority}</span>;
}

export function MultipleImprovers({
  improvers = EMPTY_IMPROVERS,
  onImproverClick,
  onViewAll,
}: MultipleImproversProps) {
  const navigate = useNavigate();

  const handleImproverClick = (improverId: string) => {
    if (onImproverClick) {
      onImproverClick(improverId);
    } else {
      navigate('/metrics/multiple-improvers');
    }
  };

  const handleViewAll = () => {
    if (onViewAll) {
      onViewAll();
    } else {
      navigate('/metrics/multiple-improvers');
    }
  };

  const isEmpty = improvers.length === 0;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <h3 className={styles.title}>What Moves the Multiple</h3>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button className={styles.infoButton}>
                  <Info size={12} />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top">
                Actions with the highest impact on valuation multiple
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        {!isEmpty && (
          <button className={styles.viewAllLink} onClick={handleViewAll}>
            View all
            <ChevronRight size={12} />
          </button>
        )}
      </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className={styles.emptyState}>
          <Info size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No recommendations yet</p>
          <p className={styles.emptySubtext}>Upload documents to get actionable insights</p>
        </div>
      ) : (
        /* List */
        <div className={styles.list}>
          {improvers.map((item, index) => {
            const config = statusConfig[item.status];
            const progressPercent = (item.progress.current / item.progress.total) * 100;

            return (
              <div
                key={item.id}
                className={styles.item}
                onClick={() => handleImproverClick(item.id)}
                style={{ animationDelay: `${index * 60}ms` }}
              >
                <div className={styles.itemContent}>
                  {/* Priority circle */}
                  <div className={styles.priorityColumn}>
                    <PriorityBadge priority={item.categories.priority} />
                  </div>

                  {/* Main content */}
                  <div className={styles.mainContent}>
                    {/* Action title + impact badge */}
                    <div className={styles.actionRow}>
                      <span className={styles.actionText}>{item.action}</span>
                      <span className={styles.impactBadge}>{item.impactLabel}</span>
                    </div>

                    {/* Meta row: Status + Effort + Progress */}
                    <div className={styles.metaRow}>
                      {/* Status badge */}
                      <div className={styles.metaItem}>
                        <div
                          className={styles.statusDot}
                          style={{ backgroundColor: config.color }}
                        />
                        <span className={cn(styles.statusText, config.className)}>
                          {config.label}
                        </span>
                      </div>

                      <span className={styles.metaDivider}>|</span>

                      {/* Effort */}
                      <div className={styles.metaItem}>
                        <span className={styles.metaLabel}>Effort:</span>
                        <LevelBadge level={item.categories.effort} variant="effort" />
                      </div>

                      <span className={styles.metaDivider}>|</span>

                      {/* Progress */}
                      <div className={styles.metaItem}>
                        <span className={styles.metaLabel}>Progress:</span>
                        <span className={styles.progressText}>
                          {item.progress.current}/{item.progress.total}
                        </span>
                        <div className={styles.progressBar}>
                          <div
                            className={styles.progressFill}
                            style={{
                              width: `${progressPercent}%`,
                              backgroundColor: config.color,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Chevron */}
                  <ChevronRight className={styles.chevron} size={16} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default MultipleImprovers;
