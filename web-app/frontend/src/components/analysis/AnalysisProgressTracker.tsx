/**
 * AnalysisProgressTracker Component
 *
 * Displays real-time progress of the analysis including stages and pillar progress.
 */

import { Activity, Check } from 'lucide-react';
import type { PillarProgressItem } from '../../api/scoringApi';
import { PILLAR_CONFIG } from '../../api/scoringApi';
import styles from '../../styles/components/analysis/AnalysisProgressTracker.module.css';

const STAGE_LABELS: Record<number, string> = {
  1: 'Extracting Metrics',
  2: 'Aggregating Pillar Data',
  3: 'Evaluating & Scoring Pillars',
  4: 'Detecting Flags',
  5: 'Calculating BDE Score & Recommendation',
};

export interface AnalysisProgressTrackerProps {
  isRunning: boolean;
  progress: number;
  stage: number;
  stageName: string;
  pillarProgress: Record<string, PillarProgressItem>;
}

function getHealthColor(status: string | null): string {
  switch (status) {
    case 'green':
      return 'var(--score-green)';
    case 'yellow':
      return 'var(--score-yellow)';
    case 'red':
      return 'var(--score-red)';
    default:
      return 'var(--text-muted)';
  }
}

export function AnalysisProgressTracker({
  isRunning,
  progress,
  stage,
  stageName,
  pillarProgress,
}: AnalysisProgressTrackerProps) {
  if (!isRunning) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>Analysis Progress</h2>
        </div>
        <div className={styles.idle}>
          <Activity size={32} className={styles.idleIcon} />
          <p className={styles.idleText}>
            No analysis is currently running. Click "Run Analysis" to start.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Analysis Progress</h2>
        <div className={styles.runningBadge}>
          <span className={styles.runningDot} />
          In Progress
        </div>
      </div>

      <div className={styles.content}>
        {/* Overall Progress Bar */}
        <div className={styles.progressSection}>
          <div className={styles.progressHeader}>
            <span className={styles.progressLabel}>{stageName || 'Processing...'}</span>
            <span className={styles.progressPercent}>{progress}%</span>
          </div>
          <div className={styles.progressBarContainer}>
            <div className={styles.progressBar} style={{ width: `${progress}%` }} />
          </div>
        </div>

        {/* Stage Indicator */}
        <div className={styles.stageSection}>
          <h3 className={styles.stageTitle}>Stages</h3>
          <div className={styles.stageList}>
            {Object.entries(STAGE_LABELS).map(([stageNum, label]) => {
              const num = parseInt(stageNum);
              const isActive = stage === num;
              const isComplete = stage > num;

              return (
                <div
                  key={stageNum}
                  className={`${styles.stageItem} ${isActive ? styles.stageItemActive : ''} ${isComplete ? styles.stageItemComplete : ''}`}
                >
                  <div className={styles.stageNumber}>
                    {isComplete ? <Check size={14} /> : num}
                  </div>
                  <span className={styles.stageLabel}>{label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Pillar Progress */}
        {Object.keys(pillarProgress).length > 0 && (
          <div className={styles.pillarSection}>
            <h3 className={styles.pillarTitle}>Pillar Progress</h3>
            <div className={styles.pillarGrid}>
              {Object.entries(pillarProgress).map(([pillarKey, pillar]) => {
                const config = PILLAR_CONFIG[pillarKey as keyof typeof PILLAR_CONFIG];
                const isProcessing = pillar.status === 'processing';
                const isComplete = pillar.status === 'completed';
                const progressColor = isComplete
                  ? getHealthColor(pillar.health_status)
                  : config?.color || 'var(--text-muted)';

                return (
                  <div
                    key={pillarKey}
                    className={`${styles.pillarItem} ${isProcessing ? styles.pillarItemProcessing : ''} ${isComplete ? styles.pillarItemComplete : ''}`}
                  >
                    <div className={styles.pillarHeader}>
                      <span
                        className={styles.pillarDot}
                        style={{ backgroundColor: progressColor }}
                      />
                      <span className={styles.pillarName}>{pillar.name}</span>
                    </div>
                    <div className={styles.pillarProgressBar}>
                      <div
                        className={styles.pillarProgressFill}
                        style={{
                          width: `${pillar.progress}%`,
                          backgroundColor: progressColor,
                        }}
                      />
                    </div>
                    {isComplete && pillar.score !== null && (
                      <div className={styles.pillarScore}>
                        Score: {pillar.score.toFixed(1)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AnalysisProgressTracker;
