/**
 * DocumentProgressContext
 *
 * Global context for managing document processing progress.
 * Maintains WebSocket connection at app-level so progress persists across page navigation.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';
import { useAuth } from './AuthContext';
import { getApiBaseUrl } from '../utils/api';

export interface DocumentProgress {
  document_id: string;
  filename: string;
  step: number;
  step_name: string;
  progress: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface DocumentProgressContextType {
  /** Map of document_id -> progress data */
  progressMap: Map<string, DocumentProgress>;
  /** WebSocket connection status */
  connectionStatus: ConnectionStatus;
  /** Last connection error */
  lastError: string | null;
  /** Register a document for progress tracking */
  trackDocument: (documentId: string, filename: string) => void;
  /** Stop tracking a document */
  untrackDocument: (documentId: string) => void;
  /** Get progress for a specific document */
  getProgress: (documentId: string) => DocumentProgress | undefined;
  /** Get all documents currently being processed */
  getProcessingDocuments: () => DocumentProgress[];
  /** Manually reconnect WebSocket */
  reconnect: () => void;
  /** Clear completed/failed documents from tracking */
  clearCompleted: () => void;
}

const DocumentProgressContext = createContext<DocumentProgressContextType | undefined>(undefined);

interface DocumentProgressProviderProps {
  children: ReactNode;
}

// Constants
const MAX_RECONNECT_ATTEMPTS = 10;
const PROGRESS_STORAGE_KEY = 'bde-document-progress';

export function DocumentProgressProvider({ children }: DocumentProgressProviderProps) {
  const { user } = useAuth();
  const tenantId = user?.tenant?.id || null;

  // Progress state - using object for easier serialization, converted to Map for API
  const [progressState, setProgressState] = useState<Record<string, DocumentProgress>>(() => {
    // Restore from localStorage on mount
    try {
      const saved = localStorage.getItem(PROGRESS_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Filter out old entries (older than 1 hour) and completed/failed
        const now = Date.now();
        const filtered: Record<string, DocumentProgress> = {};
        for (const [key, value] of Object.entries(parsed)) {
          const progress = value as DocumentProgress & { _savedAt?: number };
          const savedAt = progress._savedAt || 0;
          const age = now - savedAt;
          // Keep processing documents less than 1 hour old
          if (age < 3600000 && progress.status === 'processing') {
            filtered[key] = progress;
          }
        }
        return filtered;
      }
    } catch (e) {
      console.error('[DocumentProgress] Failed to restore from localStorage:', e);
    }
    return {};
  });

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastError, setLastError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);

  // Persist progress to localStorage whenever it changes
  useEffect(() => {
    try {
      // Add timestamp to each entry for age filtering on restore
      const toSave: Record<string, DocumentProgress & { _savedAt: number }> = {};
      for (const [key, value] of Object.entries(progressState)) {
        toSave[key] = { ...value, _savedAt: Date.now() };
      }
      localStorage.setItem(PROGRESS_STORAGE_KEY, JSON.stringify(toSave));
    } catch (e) {
      console.error('[DocumentProgress] Failed to save to localStorage:', e);
    }
  }, [progressState]);

  // WebSocket connection
  const connect = useCallback(() => {
    if (!tenantId) {
      setConnectionStatus('disconnected');
      return;
    }

    // Prevent multiple connections
    if (wsRef.current) {
      const state = wsRef.current.readyState;
      if (state === WebSocket.CONNECTING || state === WebSocket.OPEN) {
        return;
      }
    }

    setConnectionStatus('connecting');
    setLastError(null);

    const apiBaseUrl = getApiBaseUrl();
    const wsProtocol = apiBaseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiBaseUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}/api/documents/ws`;

    console.log('[DocumentProgress] Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[DocumentProgress] Connected, subscribing tenant:', tenantId);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
        ws.send(JSON.stringify({ tenant_id: tenantId }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }

          if (data.type === 'progress') {
            console.log('[DocumentProgress] Received:', data);

            setProgressState((prev) => {
              const existing = prev[data.document_id];

              // If we don't have this document tracked, and it's processing, start tracking it
              // This handles the case where document was uploaded in another tab
              if (!existing && data.status === 'processing') {
                console.log('[DocumentProgress] New document detected:', data.document_id);
              }

              return {
                ...prev,
                [data.document_id]: {
                  document_id: data.document_id,
                  filename: existing?.filename || 'Processing...',
                  step: data.step,
                  step_name: data.step_name,
                  progress: data.progress,
                  status: data.status,
                  error_message: data.error_message,
                },
              };
            });
          }
        } catch (e) {
          console.error('[DocumentProgress] Failed to parse message:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('[DocumentProgress] Disconnected:', event.code, event.reason);
        wsRef.current = null;

        if (event.code !== 1000 && event.code !== 1001) {
          setConnectionStatus('error');
          setLastError(`Connection closed: ${event.reason || 'Unknown reason'}`);
        } else {
          setConnectionStatus('disconnected');
        }

        // Reconnect with exponential backoff
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectAttemptsRef.current++;
          console.log(
            `[DocumentProgress] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})...`
          );
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        } else {
          setConnectionStatus('error');
          setLastError('Max reconnection attempts reached. Please refresh the page.');
        }
      };

      ws.onerror = (error) => {
        console.error('[DocumentProgress] Error:', error);
        setConnectionStatus('error');
        setLastError('WebSocket connection error');
      };
    } catch (error) {
      console.error('[DocumentProgress] Failed to connect:', error);
      setConnectionStatus('error');
      setLastError(error instanceof Error ? error.message : 'Failed to connect');
    }
  }, [tenantId]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.onopen = null;
      wsRef.current.close(1000, 'Client disconnecting');
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
    reconnectAttemptsRef.current = 0;
  }, []);

  // Connect when tenant is available
  useEffect(() => {
    if (tenantId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [tenantId, connect, disconnect]);

  // Track a new document
  const trackDocument = useCallback((documentId: string, filename: string) => {
    console.log('[DocumentProgress] Tracking document:', documentId, filename);
    setProgressState((prev) => ({
      ...prev,
      [documentId]: {
        document_id: documentId,
        filename,
        step: 1,
        step_name: 'Starting...',
        progress: 0,
        status: 'processing',
      },
    }));
  }, []);

  // Stop tracking a document
  const untrackDocument = useCallback((documentId: string) => {
    console.log('[DocumentProgress] Untracking document:', documentId);
    setProgressState((prev) => {
      const updated = { ...prev };
      delete updated[documentId];
      return updated;
    });
  }, []);

  // Get progress for a specific document
  const getProgress = useCallback(
    (documentId: string) => progressState[documentId],
    [progressState]
  );

  // Get all processing documents
  const getProcessingDocuments = useCallback(
    () => Object.values(progressState).filter((p) => p.status === 'processing'),
    [progressState]
  );

  // Clear completed/failed documents
  const clearCompleted = useCallback(() => {
    setProgressState((prev) => {
      const updated: Record<string, DocumentProgress> = {};
      for (const [key, value] of Object.entries(prev)) {
        if (value.status === 'processing') {
          updated[key] = value;
        }
      }
      return updated;
    });
  }, []);

  // Convert to Map for the API
  const progressMap = new Map(Object.entries(progressState));

  return (
    <DocumentProgressContext.Provider
      value={{
        progressMap,
        connectionStatus,
        lastError,
        trackDocument,
        untrackDocument,
        getProgress,
        getProcessingDocuments,
        reconnect: connect,
        clearCompleted,
      }}
    >
      {children}
    </DocumentProgressContext.Provider>
  );
}

export function useDocumentProgressContext(): DocumentProgressContextType {
  const context = useContext(DocumentProgressContext);
  if (context === undefined) {
    throw new Error('useDocumentProgressContext must be used within a DocumentProgressProvider');
  }
  return context;
}
