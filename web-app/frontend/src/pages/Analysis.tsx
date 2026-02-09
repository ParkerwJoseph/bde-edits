/**
 * Analysis Page
 *
 * Dedicated page for running BDE analysis with real-time progress tracking.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import {
  AnalysisStatus,
  AnalysisDataReadiness,
  AnalysisRunner,
  AnalysisProgressTracker,
  AnalysisResults,
} from '../components/analysis';
import { useAuth } from '../context/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import { scoringApi } from '../api/scoringApi';
import type {
  AnalysisStatusResponse,
  ScoringProgressMessage,
  PillarProgressItem,
} from '../api/scoringApi';
import { getApiBaseUrl } from '../utils/api';
import styles from '../styles/pages/Analysis.module.css';

export default function Analysis() {
  const { user } = useAuth();
  const { selectedCompanyId } = useCompany();
  const tenantId = user?.tenant?.id || null;

  // Status state
  const [status, setStatus] = useState<AnalysisStatusResponse | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [isTriggering, setIsTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Progress state
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState(0);
  const [stageName, setStageName] = useState('');
  const [pillarProgress, setPillarProgress] = useState<Record<string, PillarProgressItem>>({});

  // Result state
  const [result, setResult] = useState<{ overall_score: number; valuation_range: string } | null>(null);
  const [resultCompletedAt, setResultCompletedAt] = useState<Date | undefined>();

  // WebSocket ref
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch analysis status
  const fetchStatus = useCallback(async () => {
    if (!selectedCompanyId) {
      setStatus(null);
      setIsLoadingStatus(false);
      return;
    }

    try {
      setIsLoadingStatus(true);
      const data = await scoringApi.getAnalysisStatus(selectedCompanyId);
      setStatus(data);
      setIsRunning(data.is_running);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch analysis status:', err);
      setError('Failed to fetch analysis status');
    } finally {
      setIsLoadingStatus(false);
    }
  }, [selectedCompanyId]);

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (!tenantId || wsRef.current?.readyState === WebSocket.OPEN) return;

    const apiBaseUrl = getApiBaseUrl();
    const wsProtocol = apiBaseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiBaseUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}/api/scoring/ws`;

    console.log('[AnalysisWS] Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[AnalysisWS] Connected, sending tenant_id:', tenantId);
        ws.send(JSON.stringify({ tenant_id: tenantId }));
      };

      ws.onmessage = (event) => {
        try {
          const message: ScoringProgressMessage = JSON.parse(event.data);

          if (message.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }

          if (message.type === 'scoring_progress' && message.company_id === selectedCompanyId) {
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
                setResultCompletedAt(new Date());
              }
              fetchStatus();
            } else if (message.status === 'failed') {
              setIsRunning(false);
              setError(message.error_message || 'Analysis failed');
              fetchStatus();
            } else if (message.status === 'processing') {
              setIsRunning(true);
              setError(null);
            }
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (e) => {
        console.error('[AnalysisWS] Error:', e);
      };

      ws.onclose = (e) => {
        console.log('[AnalysisWS] Closed:', e.code, e.reason);
        if (isRunning) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, 5000);
        }
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
    }
  }, [tenantId, selectedCompanyId, isRunning, fetchStatus]);

  // Initial fetch
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // WebSocket setup when running
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
    if (!selectedCompanyId || isTriggering) return;

    setIsTriggering(true);
    setError(null);
    setResult(null);

    try {
      await scoringApi.triggerScoring(selectedCompanyId);
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
      setIsTriggering(false);
    }
  };

  // Handle dismiss result
  const handleDismissResult = () => {
    setResult(null);
    setResultCompletedAt(undefined);
  };

  // No company selected
  if (!selectedCompanyId) {
    return (
      <AppLayout title="Run Analysis" subtitle="Analyze your company data to generate BDE scores">
        <div className={styles.container}>
          <div className={styles.grid}>
            <div className={styles.fullWidth}>
              <AnalysisStatus status={null} isLoading={false} />
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Run Analysis" subtitle="Analyze your company data to generate BDE scores">
      <div className={styles.container}>
        {/* Show results banner if completed */}
        {result && (
          <AnalysisResults
            result={result}
            completedAt={resultCompletedAt}
            onDismiss={handleDismissResult}
          />
        )}

        {/* Error banner */}
        {error && !isRunning && (
          <div style={{
            padding: '16px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '12px',
            color: 'var(--score-red)',
            fontSize: '14px',
          }}>
            {error}
          </div>
        )}

        <div className={styles.grid}>
          {/* Status */}
          <AnalysisStatus status={status} isLoading={isLoadingStatus} />

          {/* Data Readiness */}
          <AnalysisDataReadiness status={status} isLoading={isLoadingStatus} />

          {/* Runner */}
          <AnalysisRunner
            status={status}
            isRunning={isRunning}
            isTriggering={isTriggering}
            onRunAnalysis={handleRunAnalysis}
          />

          {/* Progress Tracker */}
          <AnalysisProgressTracker
            isRunning={isRunning}
            progress={progress}
            stage={stage}
            stageName={stageName}
            pillarProgress={pillarProgress}
          />
        </div>
      </div>
    </AppLayout>
  );
}
