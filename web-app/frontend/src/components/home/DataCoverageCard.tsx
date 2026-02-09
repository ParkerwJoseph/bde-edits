/**
 * DataCoverageCard Component
 *
 * Displays data coverage across different pillars.
 * Shows progress bars, document counts, and overall coverage percentage.
 */

import {
  FileText,
  AlertCircle,
  CheckCircle2,
  Info,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import { Progress } from '../ui/Progress';
import styles from '../../styles/components/home/DataCoverageCard.module.css';

interface CoverageItem {
  label: string;
  icon: LucideIcon;
  coverage: number;
  docsCount: number;
  lastUpdated: string;
}

export interface DataCoverageCardProps {
  /** Custom coverage data */
  coverageData?: CoverageItem[];
  /** Callback when item is clicked */
  onItemClick?: (item: CoverageItem) => void;
}

// Empty array - no fake default data
const EMPTY_COVERAGE_DATA: CoverageItem[] = [];

const getCoverageVariant = (value: number): 'success' | 'warning' | 'error' => {
  if (value >= 80) return 'success';
  if (value >= 60) return 'warning';
  return 'error';
};

const getCoverageColorClass = (value: number): string => {
  if (value >= 80) return styles.coverageHigh;
  if (value >= 60) return styles.coverageMedium;
  return styles.coverageLow;
};

export function DataCoverageCard({
  coverageData = EMPTY_COVERAGE_DATA,
  onItemClick,
}: DataCoverageCardProps) {
  const isEmpty = coverageData.length === 0;
  const overallCoverage = isEmpty ? 0 : Math.round(
    coverageData.reduce((acc, item) => acc + item.coverage, 0) / coverageData.length
  );

  return (
    <div className={styles.card}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <FileText className={styles.headerIcon} size={20} />
          <h3 className={styles.title}>Data Coverage</h3>
        </div>
        {!isEmpty && (
          <div className={cn(styles.overallScore, getCoverageColorClass(overallCoverage))}>
            {overallCoverage}%
          </div>
        )}
      </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className={styles.emptyState}>
          <Info size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No documents uploaded</p>
          <p className={styles.emptySubtext}>Upload documents to see coverage analysis</p>
        </div>
      ) : (
        <>
          {/* Coverage Items */}
          <div className={styles.list}>
            {coverageData.map((item) => {
              const StatusIcon = item.coverage >= 80 ? CheckCircle2 : AlertCircle;

              return (
                <div
                  key={item.label}
                  className={styles.item}
                  onClick={() => onItemClick?.(item)}
                >
                  <div className={styles.itemHeader}>
                    <div className={styles.itemLeft}>
                      <item.icon className={styles.itemIcon} size={16} />
                      <span className={styles.itemLabel}>{item.label}</span>
                    </div>
                    <div className={styles.itemRight}>
                      <span className={styles.docsCount}>{item.docsCount} docs</span>
                      <StatusIcon
                        className={cn(styles.statusIcon, getCoverageColorClass(item.coverage))}
                        size={16}
                      />
                      <span className={cn(styles.itemValue, getCoverageColorClass(item.coverage))}>
                        {item.coverage}%
                      </span>
                    </div>
                  </div>
                  <Progress
                    value={item.coverage}
                    className="h-1.5"
                  />
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className={styles.footer}>
            <p className={styles.footerText}>
              Upload more documents to improve analysis confidence
            </p>
          </div>
        </>
      )}
    </div>
  );
}

export default DataCoverageCard;
