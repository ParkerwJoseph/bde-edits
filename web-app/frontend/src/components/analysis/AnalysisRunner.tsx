/**
 * AnalysisRunner Component
 *
 * Provides the Run Analysis button with status checks and confirmation.
 */

import { Play, Loader2, AlertTriangle } from 'lucide-react';
import type { AnalysisStatusResponse } from '../../api/scoringApi';
import styles from '../../styles/components/analysis/AnalysisRunner.module.css';

export interface AnalysisRunnerProps {
  status: AnalysisStatusResponse | null;
  isRunning: boolean;
  isTriggering: boolean;
  onRunAnalysis: () => void;
}

export function AnalysisRunner({
  status,
  isRunning,
  isTriggering,
  onRunAnalysis,
}: AnalysisRunnerProps) {
  const canRun = status?.can_run_analysis && !isRunning && !isTriggering;
  const hasNewData = status?.has_new_documents || status?.has_new_connector_data;
  const hasNoData = (status?.document_count || 0) === 0 && (status?.connector_count || 0) === 0;

  const getButtonText = () => {
    if (isTriggering) return 'Starting Analysis...';
    if (isRunning) return 'Analysis Running...';
    if (status?.has_score) return 'Re-run Analysis';
    return 'Run Analysis';
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>
          {status?.has_score ? 'Re-run Analysis' : 'Run Analysis'}
        </h2>
      </div>

      <div className={styles.content}>
        <div className={styles.warning}>
          <AlertTriangle size={18} className={styles.warningIcon} />
          <p className={styles.warningText}>
            Analysis typically takes 5-10 minutes to complete. You can navigate away from this page
            and return later to see the results.
          </p>
        </div>

        {canRun ? (
          <button
            className={`${styles.runButton} ${hasNewData ? styles.runButtonHighlight : ''}`}
            onClick={onRunAnalysis}
            disabled={!canRun}
          >
            {isTriggering ? (
              <Loader2 size={20} className={styles.spinner} />
            ) : (
              <Play size={20} />
            )}
            {getButtonText()}
          </button>
        ) : (
          <div className={styles.disabledMessage}>
            {isRunning ? (
              'Analysis is currently running. Please wait for it to complete.'
            ) : hasNoData ? (
              'Upload documents or connect integrations to enable analysis.'
            ) : (
              'Analysis is up to date with current data.'
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default AnalysisRunner;
