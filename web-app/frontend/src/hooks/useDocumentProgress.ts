import { useEffect, useRef, useCallback, useState } from 'react';
import { getApiBaseUrl } from '../utils/api';

export interface DocumentProgress {
  document_id: string;
  step: number;
  step_name: string;
  progress: number;
  status: 'processing' | 'completed' | 'failed';
  error_message?: string;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface UseDocumentProgressOptions {
  tenantId: string | null;
  onProgress?: (progress: DocumentProgress) => void;
  onCompleted?: (documentId: string) => void;
  onFailed?: (documentId: string, error: string) => void;
}

export function useDocumentProgress({
  tenantId,
  onProgress,
  onCompleted,
  onFailed,
}: UseDocumentProgressOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastError, setLastError] = useState<string | null>(null);

  // Use refs to store the latest callbacks to avoid stale closures
  // and prevent WebSocket reconnection when callbacks change
  const onProgressRef = useRef(onProgress);
  const onCompletedRef = useRef(onCompleted);
  const onFailedRef = useRef(onFailed);

  // Update refs when callbacks change
  useEffect(() => {
    onProgressRef.current = onProgress;
  }, [onProgress]);

  useEffect(() => {
    onCompletedRef.current = onCompleted;
  }, [onCompleted]);

  useEffect(() => {
    onFailedRef.current = onFailed;
  }, [onFailed]);

  const connect = useCallback(() => {
    if (!tenantId) {
      setConnectionStatus('disconnected');
      return;
    }

    // Prevent multiple connections - check if already connecting or connected
    if (wsRef.current) {
      const state = wsRef.current.readyState;
      if (state === WebSocket.CONNECTING) {
        console.log('[WebSocket] Connection already in progress');
        return;
      }
      if (state === WebSocket.OPEN) {
        console.log('[WebSocket] Already connected');
        return;
      }
      // Close any existing connection in CLOSING state
      if (state === WebSocket.CLOSING) {
        console.log('[WebSocket] Waiting for previous connection to close');
        return;
      }
    }

    setConnectionStatus('connecting');
    setLastError(null);

    // Get WebSocket URL from API base URL
    const apiBaseUrl = getApiBaseUrl();
    const wsProtocol = apiBaseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiBaseUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}/api/documents/ws`;

    console.log('[WebSocket] Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected, sending tenant_id');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;

        // Send tenant_id to subscribe
        ws.send(JSON.stringify({ tenant_id: tenantId }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[WebSocket] Received message:', data);

          if (data.type === 'ping') {
            // Respond to ping with pong
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }

          if (data.type === 'progress') {
            const progress: DocumentProgress = {
              document_id: data.document_id,
              step: data.step,
              step_name: data.step_name,
              progress: data.progress,
              status: data.status,
              error_message: data.error_message,
            };

            console.log('[WebSocket] Dispatching progress:', progress);
            // Use refs to call the latest callbacks
            onProgressRef.current?.(progress);

            if (data.status === 'completed') {
              console.log('[WebSocket] Document completed:', data.document_id);
              onCompletedRef.current?.(data.document_id);
            } else if (data.status === 'failed') {
              console.log('[WebSocket] Document failed:', data.document_id, data.error_message);
              onFailedRef.current?.(data.document_id, data.error_message || 'Processing failed');
            }
          }
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Don't set error status for normal closures
        if (event.code !== 1000 && event.code !== 1001) {
          setConnectionStatus('error');
          setLastError(`Connection closed: ${event.reason || 'Unknown reason'}`);
        } else {
          setConnectionStatus('disconnected');
        }

        // Reconnect with exponential backoff (increased max attempts to 10)
        if (reconnectAttemptsRef.current < 10) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectAttemptsRef.current++;
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/10)...`);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        } else {
          console.error('[WebSocket] Max reconnection attempts reached');
          setConnectionStatus('error');
          setLastError('Max reconnection attempts reached. Please refresh the page.');
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setConnectionStatus('error');
        setLastError('WebSocket connection error');
      };
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      setConnectionStatus('error');
      setLastError(error instanceof Error ? error.message : 'Failed to connect');
    }
  }, [tenantId]); // Only reconnect when tenantId changes, not when callbacks change

  const disconnect = useCallback(() => {
    console.log('[WebSocket] Disconnecting...');
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      // Remove event handlers to prevent reconnection attempts
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.onopen = null;
      wsRef.current.close(1000, 'Client disconnecting');
      wsRef.current = null;
    }
    setIsConnected(false);
    setConnectionStatus('disconnected');
    reconnectAttemptsRef.current = 0;
  }, []);

  useEffect(() => {
    if (tenantId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [tenantId, connect, disconnect]);

  return {
    isConnected,
    connectionStatus,
    lastError,
    reconnect: connect
  };
}
