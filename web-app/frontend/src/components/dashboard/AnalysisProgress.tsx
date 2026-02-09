import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { scoringApi } from '../../api/scoringApi';
import type {
  ScoringProgressMessage,
  PillarProgressItem,
  AnalysisStatusResponse,
} from '../../api/scoringApi';
import { PILLAR_CONFIG } from '../../api/scoringApi';
import { getApiBaseUrl } from '../../utils/api';
import styles from '../../styles/Dashboard.module.css';

interface AnalysisProgressProps {
  companyId: string;
  onComplete?: () => void;
}

const STAGE_LABELS: Record<number, string> = {
  1: 'Extracting Metrics',
  2: 'Aggregating Pillar Data',
  3: 'Evaluating & Scoring Pillars',
  4: 'Detecting Flags',
  5: 'Calculating BDE Score & Recommendation',
};

export default function AnalysisProgress({ companyId, onComplete }: AnalysisProgressProps) {
  const { user } = useAuth();
  const [status, setStatus] = useState<AnalysisStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // WebSocket progress state
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState(0);
  const [stageName, setStageName] = useState('');
  const [pillarProgress, setPillarProgress] = useState<Record<string, PillarProgressItem>>({});
  const [wsError, setWsError] = useState<string | null>(null);
  const [result, setResult] = useState<{ overall_score: number; valuation_range: string } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch analysis status
  const fetchStatus = useCallback(async () => {
    if (!companyId) return;
    try {
      const data = await scoringApi.getAnalysisStatus(companyId);
      setStatus(data);
      setIsRunning(data.is_running);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch analysis status:', err);
      setError('Failed to fetch analysis status');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  // Get tenant ID from user object
  const tenantId = user?.tenant?.id || null;

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (!tenantId || wsRef.current?.readyState === WebSocket.OPEN) return;

    // Get WebSocket URL from API base URL (same pattern as useDocumentProgress)
    const apiBaseUrl = getApiBaseUrl();
    const wsProtocol = apiBaseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiBaseUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}/api/scoring/ws`;

    console.log('[ScoringWS] Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[ScoringWS] Connected, sending tenant_id:', tenantId);
        // Send tenant_id to subscribe
        ws.send(JSON.stringify({ tenant_id: tenantId }));
      };

      ws.onmessage = (event) => {
        console.log('[ScoringWS] Message received:', event.data);
        try {
          const message: ScoringProgressMessage = JSON.parse(event.data);

          if (message.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }

          if (message.type === 'scoring_progress' && message.company_id === companyId) {
            setProgress(message.progress || 0);
            setStage(message.stage || 0);
            setStageName(message.stage_name || '');

            if (message.pillar_progress) {
              setPillarProgress(message.pillar_progress);
            }

            if (message.status === 'completed') {
              setIsRunning(false);
              if (message.result) {
                setResult({
                  overall_score: message.result.overall_score,
                  valuation_range: message.result.valuation_range,
                });
              }
              // Refresh status and notify parent
              fetchStatus();
              onComplete?.();
            } else if (message.status === 'failed') {
              setIsRunning(false);
              setWsError(message.error_message || 'Analysis failed');
              fetchStatus();
            } else if (message.status === 'processing') {
              setIsRunning(true);
              setWsError(null);
            }
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (e) => {
        console.error('[ScoringWS] Error:', e);
      };

      ws.onclose = (e) => {
        console.log('[ScoringWS] Closed:', e.code, e.reason);
        // Attempt to reconnect after 5 seconds if still running
        if (isRunning) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, 5000);
        }
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
    }
  }, [tenantId, companyId, isRunning, fetchStatus, onComplete]);

  // Initial fetch and WebSocket setup
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (isRunning || status?.is_running) {
      connectWebSocket();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isRunning, status?.is_running, connectWebSocket]);

  // Handle run analysis
  const handleRunAnalysis = async () => {
    if (!companyId || triggering) return;

    setTriggering(true);
    setError(null);
    setWsError(null);
    setResult(null);

    try {
      await scoringApi.triggerScoring(companyId);
      setIsRunning(true);
      setProgress(0);
      setStage(1);
      setStageName('Starting...');
      setPillarProgress({});
      connectWebSocket();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start analysis';
      setError(errorMessage);
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.analysisCard}>
        <div className={styles.analysisLoading}>Loading analysis status...</div>
      </div>
    );
  }

  // Show progress UI when running
  if (isRunning) {
    return (
      <div className={styles.analysisCard}>
        <div className={styles.analysisHeader}>
          <h3 className={styles.analysisTitle}>Running Analysis</h3>
          <span className={styles.analysisRunningBadge}>In Progress</span>
        </div>

        <div className={styles.analysisWarning}>
          This analysis may take 5-10 minutes. Please do not close this page.
        </div>

        {/* Overall Progress Bar */}
        <div className={styles.progressSection}>
          <div className={styles.progressHeader}>
            <span className={styles.progressLabel}>{stageName || 'Processing...'}</span>
            <span className={styles.progressPercent}>{progress}%</span>
          </div>
          <div className={styles.progressBarContainer}>
            <div
              className={styles.progressBar}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Stage indicator */}
        <div className={styles.stageIndicator}>
          {Object.entries(STAGE_LABELS).map(([stageNum, label]) => {
            const num = parseInt(stageNum);
            const isActive = stage === num;
            const isComplete = stage > num;
            return (
              <div
                key={stageNum}
                className={`${styles.stageItem} ${isActive ? styles.stageActive : ''} ${isComplete ? styles.stageComplete : ''}`}
              >
                <div className={styles.stageNumber}>
                  {isComplete ? '✓' : num}
                </div>
                <div className={styles.stageLabel}>{label}</div>
              </div>
            );
          })}
        </div>

        {/* Pillar Progress */}
        {Object.keys(pillarProgress).length > 0 && (
          <div className={styles.pillarProgressSection}>
            <h4 className={styles.pillarProgressTitle}>Pillar Progress</h4>
            <div className={styles.pillarProgressGrid}>
              {Object.entries(pillarProgress).map(([pillarKey, pillar]) => {
                const config = PILLAR_CONFIG[pillarKey as keyof typeof PILLAR_CONFIG];
                const isProcessing = pillar.status === 'processing';
                const isComplete = pillar.status === 'completed';

                return (
                  <div
                    key={pillarKey}
                    className={`${styles.pillarProgressItem} ${isProcessing ? styles.pillarProcessing : ''} ${isComplete ? styles.pillarComplete : ''}`}
                  >
                    <div className={styles.pillarProgressHeader}>
                      <span
                        className={styles.pillarDot}
                        style={{ backgroundColor: isComplete ? getHealthColor(pillar.health_status) : config?.color || '#6b7280' }}
                      />
                      <span className={styles.pillarName}>{pillar.name}</span>
                    </div>
                    <div className={styles.pillarProgressBarContainer}>
                      <div
                        className={styles.pillarProgressBar}
                        style={{
                          width: `${pillar.progress}%`,
                          backgroundColor: isComplete ? getHealthColor(pillar.health_status) : config?.color || '#6b7280',
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
    );
  }

  // Show completed result briefly
  if (result) {
    return (
      <div className={styles.analysisCard}>
        <div className={styles.analysisHeader}>
          <h3 className={styles.analysisTitle}>Analysis Complete</h3>
          <span className={styles.analysisCompleteBadge}>Done</span>
        </div>
        <div className={styles.analysisResult}>
          <div className={styles.resultScore}>
            <span className={styles.resultLabel}>Overall Score</span>
            <span className={styles.resultValue}>{result.overall_score}</span>
          </div>
          <div className={styles.resultValuation}>
            <span className={styles.resultLabel}>Valuation Range</span>
            <span className={styles.resultValue}>{result.valuation_range}</span>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error || wsError) {
    return (
      <div className={styles.analysisCard}>
        <div className={styles.analysisHeader}>
          <h3 className={styles.analysisTitle}>Run Analysis</h3>
        </div>
        <div className={styles.analysisError}>
          {error || wsError}
        </div>
        <button
          className={styles.runAnalysisButton}
          onClick={handleRunAnalysis}
          disabled={triggering}
        >
          {triggering ? 'Starting...' : 'Retry Analysis'}
        </button>
      </div>
    );
  }

  // Default state - show run/rerun button
  const hasNewData = status?.has_new_documents || status?.has_new_connector_data;

  return (
    <div className={styles.analysisCard}>
      <div className={styles.analysisHeader}>
        <h3 className={styles.analysisTitle}>
          {status?.has_score ? 'Re-run Analysis' : 'Run Analysis'}
        </h3>
        <div className={styles.analysisBadges}>
          {status?.has_new_documents && (
            <span className={styles.newDocsBadge}>New Documents</span>
          )}
          {status?.has_new_connector_data && (
            <span className={styles.newConnectorBadge}>New Connector Data</span>
          )}
        </div>
      </div>

      <div className={styles.analysisInfo}>
        <p className={styles.analysisMessage}>{status?.message}</p>
        <div className={styles.dataCountRow}>
          {status?.document_count !== undefined && (
            <span className={styles.docCount}>
              {status.document_count} document{status.document_count !== 1 ? 's' : ''}
            </span>
          )}
          {status?.connector_count !== undefined && status.connector_count > 0 && (
            <span className={styles.connectorCount}>
              {status.connector_count} connector{status.connector_count !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {status?.last_scored_at && (
          <p className={styles.lastScored}>
            Last analyzed: {new Date(status.last_scored_at).toLocaleDateString()}
          </p>
        )}
      </div>

      {status?.can_run_analysis ? (
        <>
          <div className={styles.analysisWarning}>
            Analysis may take 5-10 minutes to complete.
          </div>
          <button
            className={`${styles.runAnalysisButton} ${hasNewData ? styles.runAnalysisButtonHighlight : ''}`}
            onClick={handleRunAnalysis}
            disabled={triggering}
          >
            {triggering ? 'Starting...' : status?.has_score ? 'Re-run Analysis' : 'Run Analysis'}
          </button>
        </>
      ) : (
        <div className={styles.analysisDisabled}>
          {status?.document_count === 0 && status?.connector_count === 0
            ? 'Upload documents or connect integrations to enable analysis'
            : 'Analysis is up to date'}
        </div>
      )}
    </div>
  );
}

function getHealthColor(status: string | null): string {
  switch (status) {
    case 'green':
      return '#22c55e';
    case 'yellow':
      return '#f59e0b';
    case 'red':
      return '#ef4444';
    default:
      return '#6b7280';
  }
}
