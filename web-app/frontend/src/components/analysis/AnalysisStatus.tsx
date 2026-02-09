/**
 * AnalysisStatus Component
 *
 * Displays the current analysis status including score, last run date,
 * and badges for new data availability.
 */

import { FileText, Link2, Calendar } from 'lucide-react';
import type { AnalysisStatusResponse } from '../../api/scoringApi';
import styles from '../../styles/components/analysis/AnalysisStatus.module.css';

export interface AnalysisStatusProps {
  status: AnalysisStatusResponse | null;
  isLoading: boolean;
}

export function AnalysisStatus({ status, isLoading }: AnalysisStatusProps) {
  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading analysis status...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Analysis Status</h2>
        <div className={styles.badges}>
          {status?.is_running && (
            <span className={`${styles.badge} ${styles.runningBadge}`}>Running</span>
          )}
          {status?.has_new_documents && (
            <span className={`${styles.badge} ${styles.newDocsBadge}`}>New Documents</span>
          )}
          {status?.has_new_connector_data && (
            <span className={`${styles.badge} ${styles.newConnectorBadge}`}>New Connector Data</span>
          )}
        </div>
      </div>

      <div className={styles.content}>
        {status?.has_score ? (
          <div className={styles.scoreSection}>
            <div className={styles.scoreInfo}>
              <div className={styles.scoreLabel}>Analysis Available</div>
              <div className={styles.valuationRange}>
                Last analyzed: {status.last_scored_at ? new Date(status.last_scored_at).toLocaleDateString() : 'Unknown'}
              </div>
            </div>
          </div>
        ) : (
          <div className={styles.noScore}>
            <p className={styles.noScoreText}>
              No analysis has been run yet. Run your first analysis to get a BDE score.
            </p>
          </div>
        )}

        <div className={styles.metaRow}>
          <div className={styles.metaItem}>
            <FileText size={16} className={styles.metaIcon} />
            <span>{status?.document_count || 0} documents</span>
          </div>
          <div className={styles.metaItem}>
            <Link2 size={16} className={styles.metaIcon} />
            <span>{status?.connector_count || 0} connectors</span>
          </div>
          {status?.last_scored_at && (
            <div className={styles.metaItem}>
              <Calendar size={16} className={styles.metaIcon} />
              <span>Last run: {new Date(status.last_scored_at).toLocaleDateString()}</span>
            </div>
          )}
        </div>

        {status?.message && <p className={styles.message}>{status.message}</p>}
      </div>
    </div>
  );
}

export default AnalysisStatus;
