/**
 * ProcessingJobs Component
 *
 * Displays list of documents being processed with their status.
 * Shows real-time progress through all processing stages via WebSocket.
 * Based on reference UI design.
 */

import { Loader2 } from 'lucide-react';
import { getFileIcon } from '../../utils/fileUtils';
import styles from '../../styles/components/ingestion/ProcessingJobs.module.css';

// Processing steps for progress visualization
const PROCESSING_STEPS = [
  { step: 1, name: 'Uploading' },
  { step: 2, name: 'Analyzing' },
  { step: 3, name: 'Chunking' },
  { step: 4, name: 'Embeddings' },
  { step: 5, name: 'Storing' },
  { step: 6, name: 'Done' },
];

export interface ProcessingJob {
  id: string;
  filename: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  step?: number;
  stepName?: string;
  progress?: number;
  error?: string;
}

export interface ProcessingJobsProps {
  jobs: ProcessingJob[];
}

export function ProcessingJobs({ jobs }: ProcessingJobsProps) {
  const activeJobs = jobs.filter(
    (job) => job.status === 'pending' || job.status === 'uploading' || job.status === 'processing'
  );

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Processing Jobs</h2>
        <p className={styles.description}>Track document extraction and analysis status</p>
      </div>

      <div className={styles.content}>
        {activeJobs.length === 0 ? (
          <div className={styles.empty}>
            No processing jobs yet. Upload documents to get started.
          </div>
        ) : (
          <div className={styles.jobList}>
            {activeJobs.map((job) => (
              <div key={job.id} className={styles.jobItem}>
                <div className={styles.jobIcon}>
                  {getFileIcon(job.filename)}
                </div>

                <div className={styles.jobInfo}>
                  <span className={styles.jobFilename}>{job.filename}</span>
                  <div className={styles.jobStatus}>
                    {job.status === 'pending' && (
                      <span className={styles.statusPending}>Pending</span>
                    )}
                    {job.status === 'uploading' && (
                      <>
                        <Loader2 className={styles.spinner} size={12} />
                        <span>Uploading...</span>
                      </>
                    )}
                    {job.status === 'processing' && (
                      <>
                        <Loader2 className={styles.spinner} size={12} />
                        <span>{job.stepName || 'Processing...'}</span>
                      </>
                    )}
                  </div>
                </div>

                {(job.status === 'uploading' || job.status === 'processing') && (
                  <div className={styles.progressWrapper}>
                    <div className={styles.progressSection}>
                      <div className={styles.progressBar}>
                        <div
                          className={styles.progressFill}
                          style={{ width: `${job.progress || 0}%` }}
                        />
                      </div>
                      <span className={styles.progressText}>{job.progress || 0}%</span>
                    </div>
                    <div className={styles.progressSteps}>
                      {PROCESSING_STEPS.map((step) => {
                        const currentStep = job.step || (job.status === 'uploading' ? 1 : 0);
                        const isCompleted = currentStep > step.step;
                        const isActive = currentStep === step.step;
                        return (
                          <span
                            key={step.step}
                            className={`${styles.progressStep} ${isCompleted ? styles.progressStepCompleted : ''} ${isActive ? styles.progressStepActive : ''}`}
                          >
                            <span className={styles.stepIndicator}>
                              {isCompleted ? '✓' : isActive ? '→' : '○'}
                            </span>
                            <span className={styles.stepName}>{step.name}</span>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ProcessingJobs;
