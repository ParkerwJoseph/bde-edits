/**
 * Ingestion Page
 *
 * Data ingestion interface for uploading documents.
 * Based on reference UI design.
 */

import { useState, useRef, useEffect } from 'react';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { AppLayout } from '../components/layout/AppLayout';
import { IngestionUploadZone } from '../components/ingestion/IngestionUploadZone';
import { DocumentCoverage } from '../components/ingestion/DocumentCoverage';
import { ProcessingJobs, type ProcessingJob } from '../components/ingestion/ProcessingJobs';
import { RecentDocuments } from '../components/ingestion/RecentDocuments';
import { Button } from '../components/ui/Button';
import { documentApi } from '../api/documentApi';
import { useCompany } from '../contexts/CompanyContext';
import { useToast } from '../components/common/Toast';
import { useDocumentProgressContext, type ConnectionStatus } from '../context/DocumentProgressContext';
import { getExtension, ALL_ALLOWED_EXTENSIONS } from '../utils/fileUtils';
import styles from '../styles/pages/Ingestion.module.css';

// Connection status labels
const CONNECTION_STATUS_LABELS: Record<ConnectionStatus, string> = {
  connected: 'Real-time updates active',
  connecting: 'Connecting...',
  disconnected: 'Disconnected',
  error: 'Connection error',
};

// Helper to get status class
function getStatusClass(status: ConnectionStatus): string {
  switch (status) {
    case 'connected':
      return styles.connectionStatusConnected;
    case 'connecting':
      return styles.connectionStatusConnecting;
    case 'error':
      return styles.connectionStatusError;
    default:
      return styles.connectionStatusDisconnected;
  }
}

function getDotClass(status: ConnectionStatus): string {
  switch (status) {
    case 'connected':
      return styles.connectionDotConnected;
    case 'connecting':
      return styles.connectionDotConnecting;
    case 'error':
      return styles.connectionDotError;
    default:
      return styles.connectionDotDisconnected;
  }
}

interface SelectedFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  documentId?: string;
  error?: string;
  progress?: {
    step: number;
    stepName: string;
    progress: number;
  };
}

export default function Ingestion() {
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const { selectedCompanyId } = useCompany();
  const toast = useToast();

  // Use global progress context - WebSocket stays connected across page navigation
  const { progressMap, connectionStatus, reconnect, trackDocument } = useDocumentProgressContext();

  // Track which document IDs have already been notified to prevent duplicates
  const notifiedRef = useRef<Set<string>>(new Set());

  // Sync global progress state with local files state
  useEffect(() => {
    setFiles((prev) => {
      let hasChanges = false;
      const updated = prev.map((f) => {
        if (!f.documentId) return f;

        const globalProgress = progressMap.get(f.documentId);
        if (!globalProgress) return f;

        // Check if status changed to completed
        if (globalProgress.status === 'completed' && f.status !== 'completed') {
          hasChanges = true;

          // Show toast notification (prevent duplicates)
          if (!notifiedRef.current.has(`completed-${f.documentId}`)) {
            notifiedRef.current.add(`completed-${f.documentId}`);
            queueMicrotask(() => {
              toast.success('Document processed', `"${f.file.name}" has been processed successfully.`);
            });
            setRefreshTrigger((t) => t + 1);
          }

          return {
            ...f,
            status: 'completed' as const,
            progress: { step: 6, stepName: 'Completed', progress: 100 },
          };
        }

        // Check if status changed to failed
        if (globalProgress.status === 'failed' && f.status !== 'failed') {
          hasChanges = true;

          // Show toast notification (prevent duplicates)
          if (!notifiedRef.current.has(`failed-${f.documentId}`)) {
            notifiedRef.current.add(`failed-${f.documentId}`);
            queueMicrotask(() => {
              toast.error('Processing failed', `"${f.file.name}" failed: ${globalProgress.error_message || 'Unknown error'}`);
            });
          }

          return {
            ...f,
            status: 'failed' as const,
            error: globalProgress.error_message || 'Processing failed',
          };
        }

        // Update progress if still processing
        if (globalProgress.status === 'processing') {
          const newProgress = {
            step: globalProgress.step,
            stepName: globalProgress.step_name,
            progress: globalProgress.progress,
          };

          if (
            f.progress?.step !== newProgress.step ||
            f.progress?.progress !== newProgress.progress
          ) {
            hasChanges = true;
            return { ...f, progress: newProgress };
          }
        }

        return f;
      });

      return hasChanges ? updated : prev;
    });
  }, [progressMap, toast]);

  // File handling
  const handleFilesSelected = async (newFiles: File[]) => {
    if (!selectedCompanyId) {
      alert('Please select a company from the sidebar first');
      return;
    }

    const processedFiles: SelectedFile[] = newFiles
      .filter((file) => {
        const ext = getExtension(file.name);
        return ALL_ALLOWED_EXTENSIONS.includes(ext);
      })
      .map((file) => ({
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        file,
        status: 'pending' as const,
      }));

    if (processedFiles.length === 0) return;

    setFiles((prev) => [...prev, ...processedFiles]);

    // Upload files sequentially
    for (const fileItem of processedFiles) {
      await uploadFile(fileItem);
    }
  };

  const uploadFile = async (fileItem: SelectedFile) => {
    setFiles((prev) =>
      prev.map((f) => (f.id === fileItem.id ? { ...f, status: 'uploading' as const } : f))
    );

    try {
      const response = await documentApi.upload(fileItem.file, selectedCompanyId!);
      console.log('[Ingestion] Upload complete, documentId:', response.document_id);

      // Track document in global context for progress updates across page navigation
      trackDocument(response.document_id, fileItem.file.name);

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id
            ? {
                ...f,
                status: 'processing' as const,
                documentId: response.document_id,
                // Set initial progress to show upload is complete, now processing
                progress: {
                  step: 2,
                  stepName: 'Analyzing Document',
                  progress: 20,
                },
              }
            : f
        )
      );
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            'Upload failed';

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id ? { ...f, status: 'failed' as const, error: errorMessage } : f
        )
      );
    }
  };

  // Convert files to processing jobs format - combine local files with global progress
  const localJobIds = new Set(files.map((f) => f.documentId).filter(Boolean));

  // Jobs from local files state (current session uploads)
  const localJobs: ProcessingJob[] = files
    .filter((f) => f.status !== 'completed')
    .map((f) => ({
      id: f.id,
      filename: f.file.name,
      status: f.status,
      step: f.progress?.step,
      stepName: f.progress?.stepName,
      progress: f.progress?.progress,
      error: f.error,
    }));

  // Jobs from global context that aren't in local files (from previous navigation)
  const globalJobs: ProcessingJob[] = Array.from(progressMap.values())
    .filter((doc) => doc.status === 'processing' && !localJobIds.has(doc.document_id))
    .map((doc) => ({
      id: doc.document_id,
      filename: doc.filename,
      status: 'processing' as const,
      step: doc.step,
      stepName: doc.step_name,
      progress: doc.progress,
    }));

  // Combine both - global jobs first (they were started earlier), then local
  const processingJobs: ProcessingJob[] = [...globalJobs, ...localJobs];

  const isUploading = files.some((f) => f.status === 'uploading' || f.status === 'processing');
  const hasProcessingFiles = files.some(f => f.status === 'processing') || globalJobs.length > 0;

  return (
    <AppLayout title="Ingestion" subtitle="Upload and process your business documents">
      <div className={styles.container}>
        {/* Upload Zone */}
        <IngestionUploadZone
          onFilesSelected={handleFilesSelected}
          disabled={!selectedCompanyId || isUploading}
        />

        {/* Document Coverage */}
        <DocumentCoverage
          companyId={selectedCompanyId}
          refreshTrigger={refreshTrigger}
        />

        {/* Connection Status and Processing Jobs */}
        {(processingJobs.length > 0 || globalJobs.length > 0 || connectionStatus === 'error') && (
          <div className={styles.statusWrapper}>
            <div className={`${styles.connectionStatus} ${getStatusClass(connectionStatus)}`}>
              <span className={`${styles.connectionDot} ${getDotClass(connectionStatus)}`} />
              {connectionStatus === 'connected' ? (
                <Wifi size={14} />
              ) : (
                <WifiOff size={14} />
              )}
              <span>{CONNECTION_STATUS_LABELS[connectionStatus]}</span>
              {(connectionStatus === 'error' || connectionStatus === 'disconnected') && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={reconnect}
                  className={styles.reconnectButton}
                >
                  <RefreshCw size={12} />
                  Reconnect
                </Button>
              )}
            </div>
            {hasProcessingFiles && (
              <div className={styles.pollingBadge}>
                <span className={styles.pollingDot} />
                Checking status
              </div>
            )}
          </div>
        )}

        {/* Processing Jobs */}
        <ProcessingJobs jobs={processingJobs} />

        {/* Recent Documents */}
        <RecentDocuments
          companyId={selectedCompanyId}
          refreshTrigger={refreshTrigger}
        />
      </div>
    </AppLayout>
  );
}
