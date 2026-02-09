/**
 * TopExitRisks Component
 *
 * Displays top exit risks with severity indicators, values, and delta badges.
 * Vertical list layout with left border accents.
 */

import { useNavigate } from 'react-router-dom';
import { ArrowRight, Info, ChevronRight } from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/Tooltip';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/home/TopExitRisks.module.css';

type DeltaType = 'neutral' | 'positive' | 'negative';
type Severity = 'critical' | 'high' | 'medium';

interface ExitRisk {
  id: string;
  title: string;
  value: string;
  delta: string;
  deltaType: DeltaType;
  severity: Severity;
}

export interface TopExitRisksProps {
  /** Custom risks data */
  risks?: ExitRisk[];
  /** Callback when risk is clicked */
  onRiskClick?: (riskId: string) => void;
  /** Callback for view all */
  onViewAll?: () => void;
}

// Empty array - no fake default data
const EMPTY_RISKS: ExitRisk[] = [];

const severityConfig: Record<Severity, { color: string }> = {
  critical: { color: 'hsl(var(--kpi-high-risk))' },
  high: { color: 'hsl(var(--kpi-at-risk))' },
  medium: { color: 'hsl(var(--kpi-watch))' },
};

export function TopExitRisks({
  risks = EMPTY_RISKS,
  onRiskClick,
  onViewAll,
}: TopExitRisksProps) {
  const navigate = useNavigate();

  const handleRiskClick = (riskId: string) => {
    if (onRiskClick) {
      onRiskClick(riskId);
    } else {
      navigate('/metrics/top-risks');
    }
  };

  const handleViewAll = () => {
    if (onViewAll) {
      onViewAll();
    } else {
      navigate('/metrics/top-risks');
    }
  };

  const isEmpty = risks.length === 0;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerSection}>
        <div className={styles.titleRow}>
          <h3 className={styles.title}>Performance Metrics</h3>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button className={styles.infoButton}>
                  <Info size={12} />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top">
                Key risks that buyers will evaluate during due diligence
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <p className={styles.subtitle}>What buyers will push back on</p>
      </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className={styles.emptyState}>
          <Info size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No metrics available yet</p>
          <p className={styles.emptySubtext}>Upload documents to analyze performance metrics</p>
        </div>
      ) : (
        <>
          {/* Risk List */}
          <div className={styles.riskList}>
            {risks.map((risk, index) => {
              const config = severityConfig[risk.severity];

              return (
                <div
                  key={risk.id}
                  className={styles.riskItem}
                  onClick={() => handleRiskClick(risk.id)}
                  style={{
                    animationDelay: `${index * 80}ms`,
                  }}
                >
                  {/* Left section with accent bar */}
                  <div className={styles.riskLeft}>
                    <div
                      className={styles.accentBar}
                      style={{ backgroundColor: config.color }}
                    />
                    <div className={styles.riskContent}>
                      <span className={styles.riskTitle}>{risk.title}</span>
                      <span className={styles.riskValue}>{risk.value}</span>
                    </div>
                  </div>

                  {/* Right section - Delta badge */}
                  <div className={styles.riskRight}>
                    <span
                      className={cn(
                        styles.deltaBadge,
                        risk.deltaType === 'positive' && styles.deltaPositive,
                        risk.deltaType === 'negative' && styles.deltaNegative,
                        risk.deltaType === 'neutral' && styles.deltaNeutral
                      )}
                    >
                      {risk.delta}
                    </span>
                    <ArrowRight className={styles.arrowIcon} size={16} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* View all link */}
          <button className={styles.viewAllButton} onClick={handleViewAll}>
            View all metrics
            <ChevronRight size={16} />
          </button>
        </>
      )}
    </div>
  );
}

export default TopExitRisks;
