/**
 * AnalysisResults Component
 *
 * Displays the results of a completed analysis with score and valuation.
 */

import { Link } from 'react-router-dom';
import { CheckCircle, ArrowRight, X } from 'lucide-react';
import styles from '../../styles/components/analysis/AnalysisResults.module.css';

export interface AnalysisResultsProps {
  result: {
    overall_score: number;
    valuation_range: string;
  } | null;
  completedAt?: Date;
  onDismiss: () => void;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'var(--score-green)';
  if (score >= 60) return 'var(--score-yellow)';
  return 'var(--score-red)';
}

export function AnalysisResults({ result, completedAt, onDismiss }: AnalysisResultsProps) {
  if (!result) {
    return null;
  }

  const scoreColor = getScoreColor(result.overall_score);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Analysis Complete</h2>
        <div className={styles.completeBadge}>
          <CheckCircle size={14} />
          Done
        </div>
      </div>

      <div className={styles.content}>
        <div className={styles.scoreSection}>
          <div
            className={styles.scoreCircle}
            style={{
              '--score-percent': result.overall_score,
              '--score-color': scoreColor,
            } as React.CSSProperties}
          >
            <div className={styles.scoreInner}>
              <span className={styles.scoreValue}>{result.overall_score}</span>
              <span className={styles.scoreLabel}>BDE Score</span>
            </div>
          </div>

          <div className={styles.scoreInfo}>
            <div className={styles.scorePrimary}>BDE Score: {result.overall_score}/100</div>
            <div className={styles.scoreSecondary}>
              <div className={styles.valuationRange}>
                Valuation Range: <span className={styles.valuationValue}>{result.valuation_range}</span>
              </div>
              {completedAt && (
                <div className={styles.timestamp}>
                  Completed: {completedAt.toLocaleString()}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className={styles.actions}>
          <Link to="/analytics" className={styles.viewButton}>
            View Full Analytics
            <ArrowRight size={16} />
          </Link>
          <button className={styles.dismissButton} onClick={onDismiss}>
            <X size={16} />
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

export default AnalysisResults;
