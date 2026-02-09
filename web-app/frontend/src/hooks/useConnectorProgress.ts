import { useEffect, useRef, useCallback, useState } from 'react';
import { getApiBaseUrl } from '../utils/api';

export type ConnectorType = 'quickbooks' | 'carbonvoice';

export interface ConnectorProgress {
  connector_config_id: string;
  connector_type?: ConnectorType;
  step: number;
  step_name: string;
  progress: number;
  status: 'processing' | 'completed' | 'failed';
  current_entity?: string;
  entities_completed?: string[];
  records_processed?: number;
  chunks_created?: number;
  error_message?: string;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface UseConnectorProgressOptions {
  tenantId: string | null;
  connectorType: ConnectorType;
  onProgress?: (progress: ConnectorProgress) => void;
  onCompleted?: (connectorConfigId: string, chunksCreated: number) => void;
  onFailed?: (connectorConfigId: string, error: string) => void;
}

export function useConnectorProgress({
  tenantId,
  connectorType,
  onProgress,
  onCompleted,
  onFailed,
}: UseConnectorProgressOptions) {
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
        console.log('[ConnectorWebSocket] Connection already in progress');
        return;
      }
      if (state === WebSocket.OPEN) {
        console.log('[ConnectorWebSocket] Already connected');
        return;
      }
      // Close any existing connection in CLOSING state
      if (state === WebSocket.CLOSING) {
        console.log('[ConnectorWebSocket] Waiting for previous connection to close');
        return;
      }
    }

    setConnectionStatus('connecting');
    setLastError(null);

    // Get WebSocket URL from API base URL
    const apiBaseUrl = getApiBaseUrl();
    const wsProtocol = apiBaseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiBaseUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}/api/connectors/${connectorType}/ws/${tenantId}`;

    console.log('[ConnectorWebSocket] Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[ConnectorWebSocket] Connected');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[ConnectorWebSocket] Received message:', data);

          // Handle ping/pong
          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }

          if (data.type === 'pong') {
            return;
          }

          // Handle ingestion progress
          if (data.type === 'ingestion_progress') {
            const progress: ConnectorProgress = {
              connector_config_id: data.connector_config_id,
              step: data.step,
              step_name: data.step_name,
              progress: data.progress,
              status: data.status,
              current_entity: data.current_entity,
              entities_completed: data.entities_completed,
              records_processed: data.records_processed,
              chunks_created: data.chunks_created,
              error_message: data.error_message,
            };

            console.log('[ConnectorWebSocket] Dispatching progress:', progress);
            // Use refs to call the latest callbacks
            onProgressRef.current?.(progress);

            if (data.status === 'completed') {
              console.log('[ConnectorWebSocket] Connector completed:', data.connector_config_id);
              onCompletedRef.current?.(data.connector_config_id, data.chunks_created || 0);
            } else if (data.status === 'failed') {
              console.log('[ConnectorWebSocket] Connector failed:', data.connector_config_id, data.error_message);
              onFailedRef.current?.(data.connector_config_id, data.error_message || 'Ingestion failed');
            }
          }
        } catch (e) {
          console.error('[ConnectorWebSocket] Failed to parse message:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('[ConnectorWebSocket] Disconnected:', event.code, event.reason);
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
          console.log(`[ConnectorWebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/10)...`);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        } else {
          console.error('[ConnectorWebSocket] Max reconnection attempts reached');
          setConnectionStatus('error');
          setLastError('Max reconnection attempts reached. Please refresh the page.');
        }
      };

      ws.onerror = (error) => {
        console.error('[ConnectorWebSocket] Error:', error);
        setConnectionStatus('error');
        setLastError('WebSocket connection error');
      };
    } catch (error) {
      console.error('[ConnectorWebSocket] Failed to connect:', error);
      setConnectionStatus('error');
      setLastError(error instanceof Error ? error.message : 'Failed to connect');
    }
  }, [tenantId, connectorType]); // Only reconnect when tenantId or connectorType changes, not when callbacks change

  const disconnect = useCallback(() => {
    console.log('[ConnectorWebSocket] Disconnecting...');
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
    reconnect: connect,
    disconnect
  };
}
