import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle } from 'lucide-react';
import { AppLayout } from '../components/layout/AppLayout';
import Loader from '../components/common/Loader';
import ConfirmModal from '../components/common/ConfirmModal';
import {
  quickbooksApi,
  type ConnectorConfig as QbConnectorConfig,
  type EntityInfo as QbEntityInfo,
  type SyncLog as QbSyncLog,
  type ConnectorStats as QbConnectorStats,
} from '../api/quickbooksApi';
import {
  carbonvoiceApi,
  type ConnectorConfig as CvConnectorConfig,
  type EntityInfo as CvEntityInfo,
  type SyncLog as CvSyncLog,
  type ConnectorStats as CvConnectorStats,
} from '../api/carbonvoiceApi';
import { useConnectorProgress, type ConnectorProgress } from '../hooks/useConnectorProgress';
import { useAuth } from '../context/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import styles from '../styles/Connectors.module.css';

// Type for connector type identifiers
type ConnectorType = 'quickbooks' | 'carbonvoice';

type ConnectionStatus = 'connected' | 'disconnected' | 'expired' | 'error';

// Define all available connectors
interface ConnectorDefinition {
  id: string;
  name: string;
  shortName: string;
  description: string;
  features: string[];
  iconClass: string;
  isAvailable: boolean;
}

const AVAILABLE_CONNECTORS: ConnectorDefinition[] = [
  {
    id: 'quickbooks',
    name: 'QuickBooks Online',
    shortName: 'QB',
    description: 'Connect to QuickBooks Online to sync financial data including invoices, bills, payments, and reports.',
    features: ['Invoices', 'Bills', 'P&L Reports', 'Balance Sheet'],
    iconClass: '', // default green
    isAvailable: true,
  },
  {
    id: 'carbonvoice',
    name: 'Carbon Voice',
    shortName: 'CV',
    description: 'Connect to Carbon Voice for conversation data, action items, and team collaboration insights.',
    features: ['Workspaces', 'Channels', 'Messages', 'Action Items'],
    iconClass: styles.connectorIconCarbonVoice,
    isAvailable: true,
  },
];

interface SyncState {
  syncing: boolean;
  currentSyncId: string | null;
  progress: string;
}

// Ingestion processing steps for progress bar
const INGESTION_STEPS = [
  { step: 1, name: 'Loading Config' },
  { step: 2, name: 'Querying Data' },
  { step: 3, name: 'Processing' },
  { step: 4, name: 'Embeddings' },
  { step: 5, name: 'Storing' },
  { step: 6, name: 'Done' },
];

interface IngestionState {
  isProcessing: boolean;
  connectorConfigId: string | null;
  step: number;
  stepName: string;
  progress: number;
  currentEntity: string | null;
  entitiesCompleted: string[];
  recordsProcessed: number;
  chunksCreated: number;
}

// Helper to get API for a connector type
const getConnectorApi = (type: ConnectorType) => {
  return type === 'carbonvoice' ? carbonvoiceApi : quickbooksApi;
};

export default function Connectors() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Use global company context
  const { selectedCompanyId } = useCompany();

  // QuickBooks Connector state
  const [qbConnector, setQbConnector] = useState<QbConnectorConfig | null>(null);
  const [loadingQbConnector, setLoadingQbConnector] = useState(false);
  const [connectingQb, setConnectingQb] = useState(false);

  // Carbon Voice Connector state
  const [cvConnector, setCvConnector] = useState<CvConnectorConfig | null>(null);
  const [loadingCvConnector, setLoadingCvConnector] = useState(false);
  const [connectingCv, setConnectingCv] = useState(false);

  // QuickBooks Entity selection
  const [qbAvailableEntities, setQbAvailableEntities] = useState<QbEntityInfo[]>([]);
  const [qbSelectedEntities, setQbSelectedEntities] = useState<string[]>([]);
  const [loadingQbEntities, setLoadingQbEntities] = useState(false);
  const [savingQbEntities, setSavingQbEntities] = useState(false);

  // Carbon Voice Entity selection
  const [cvAvailableEntities, setCvAvailableEntities] = useState<CvEntityInfo[]>([]);
  const [cvSelectedEntities, setCvSelectedEntities] = useState<string[]>([]);
  const [loadingCvEntities, setLoadingCvEntities] = useState(false);
  const [savingCvEntities, setSavingCvEntities] = useState(false);

  // QuickBooks Sync state
  const [qbSyncState, setQbSyncState] = useState<SyncState>({
    syncing: false,
    currentSyncId: null,
    progress: '',
  });
  const [qbSyncLogs, setQbSyncLogs] = useState<QbSyncLog[]>([]);

  // Carbon Voice Sync state
  const [cvSyncState, setCvSyncState] = useState<SyncState>({
    syncing: false,
    currentSyncId: null,
    progress: '',
  });
  const [cvSyncLogs, setCvSyncLogs] = useState<CvSyncLog[]>([]);

  // Stats
  const [qbStats, setQbStats] = useState<QbConnectorStats | null>(null);
  const [cvStats, setCvStats] = useState<CvConnectorStats | null>(null);

  // QuickBooks Ingestion with progress tracking
  const [qbIngestionState, setQbIngestionState] = useState<IngestionState>({
    isProcessing: false,
    connectorConfigId: null,
    step: 0,
    stepName: '',
    progress: 0,
    currentEntity: null,
    entitiesCompleted: [],
    recordsProcessed: 0,
    chunksCreated: 0,
  });

  // Carbon Voice Ingestion with progress tracking
  const [cvIngestionState, setCvIngestionState] = useState<IngestionState>({
    isProcessing: false,
    connectorConfigId: null,
    step: 0,
    stepName: '',
    progress: 0,
    currentEntity: null,
    entitiesCompleted: [],
    recordsProcessed: 0,
    chunksCreated: 0,
  });

  // Get tenant ID for WebSocket connection
  const { user } = useAuth();
  const tenantId = user?.tenant?.id || null;

  // Modals
  const [showDisconnectModal, setShowDisconnectModal] = useState<ConnectorType | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);

  // Error/success messages
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Track if we need to reload after OAuth
  const [pendingOAuthReload, setPendingOAuthReload] = useState<ConnectorType | null>(null);

  // WebSocket progress handlers for ingestion
  const handleIngestionProgress = useCallback((progress: ConnectorProgress) => {
    // Check if it's for QuickBooks connector
    if (progress.connector_config_id === qbConnector?.id) {
      setQbIngestionState((prev) => ({
        ...prev,
        isProcessing: progress.status === 'processing',
        connectorConfigId: progress.connector_config_id,
        step: progress.step,
        stepName: progress.step_name,
        progress: progress.progress,
        currentEntity: progress.current_entity || null,
        entitiesCompleted: progress.entities_completed || [],
        recordsProcessed: progress.records_processed || 0,
        chunksCreated: progress.chunks_created || 0,
      }));
    }
    // Check if it's for Carbon Voice connector
    if (progress.connector_config_id === cvConnector?.id) {
      setCvIngestionState((prev) => ({
        ...prev,
        isProcessing: progress.status === 'processing',
        connectorConfigId: progress.connector_config_id,
        step: progress.step,
        stepName: progress.step_name,
        progress: progress.progress,
        currentEntity: progress.current_entity || null,
        entitiesCompleted: progress.entities_completed || [],
        recordsProcessed: progress.records_processed || 0,
        chunksCreated: progress.chunks_created || 0,
      }));
    }
  }, [qbConnector?.id, cvConnector?.id]);

  const handleIngestionCompleted = useCallback((connectorConfigId: string, chunksCreated: number) => {
    // QuickBooks completion
    if (connectorConfigId === qbConnector?.id) {
      setQbIngestionState({
        isProcessing: false,
        connectorConfigId: null,
        step: 6,
        stepName: 'Completed',
        progress: 100,
        currentEntity: null,
        entitiesCompleted: [],
        recordsProcessed: 0,
        chunksCreated,
      });
      setSuccess(`QuickBooks ingestion completed! ${chunksCreated} chunks created.`);
      loadQbStats(qbConnector.id);
    }
    // Carbon Voice completion
    if (connectorConfigId === cvConnector?.id) {
      setCvIngestionState({
        isProcessing: false,
        connectorConfigId: null,
        step: 6,
        stepName: 'Completed',
        progress: 100,
        currentEntity: null,
        entitiesCompleted: [],
        recordsProcessed: 0,
        chunksCreated,
      });
      setSuccess(`Carbon Voice ingestion completed! ${chunksCreated} chunks created.`);
      loadCvStats(cvConnector.id);
    }
  }, [qbConnector?.id, cvConnector?.id]);

  const handleIngestionFailed = useCallback((connectorConfigId: string, errorMsg: string) => {
    // QuickBooks failure
    if (connectorConfigId === qbConnector?.id) {
      setQbIngestionState((prev) => ({
        ...prev,
        isProcessing: false,
      }));
      setError(`QuickBooks ingestion failed: ${errorMsg}`);
      if (qbConnector?.id) {
        loadQbStats(qbConnector.id);
      }
    }
    // Carbon Voice failure
    if (connectorConfigId === cvConnector?.id) {
      setCvIngestionState((prev) => ({
        ...prev,
        isProcessing: false,
      }));
      setError(`Carbon Voice ingestion failed: ${errorMsg}`);
      if (cvConnector?.id) {
        loadCvStats(cvConnector.id);
      }
    }
  }, [qbConnector?.id, cvConnector?.id]);

  // Connect to WebSocket for real-time QuickBooks ingestion progress
  useConnectorProgress({
    tenantId,
    connectorType: 'quickbooks',
    onProgress: handleIngestionProgress,
    onCompleted: handleIngestionCompleted,
    onFailed: handleIngestionFailed,
  });

  // Connect to WebSocket for real-time Carbon Voice ingestion progress
  useConnectorProgress({
    tenantId,
    connectorType: 'carbonvoice',
    onProgress: handleIngestionProgress,
    onCompleted: handleIngestionCompleted,
    onFailed: handleIngestionFailed,
  });

  // Handle OAuth callback params
  useEffect(() => {
    const oauthSuccess = searchParams.get('oauth_success');
    const oauthError = searchParams.get('oauth_error');
    const connectorType = searchParams.get('connector_type') as ConnectorType | null;

    if (oauthSuccess === 'true') {
      const connectorName = connectorType === 'carbonvoice' ? 'Carbon Voice' : 'QuickBooks';
      setSuccess(`${connectorName} connected successfully!`);
      setPendingOAuthReload(connectorType || 'quickbooks');
      // Clear URL params
      setSearchParams({});
    } else if (oauthError) {
      setError(`OAuth failed: ${decodeURIComponent(oauthError)}`);
      setSearchParams({});
    }
  }, [searchParams, setSearchParams]);

  // Handle pending OAuth reload
  useEffect(() => {
    if (pendingOAuthReload && selectedCompanyId) {
      if (pendingOAuthReload === 'quickbooks') {
        loadQbConnector();
      } else if (pendingOAuthReload === 'carbonvoice') {
        loadCvConnector();
      }
      setPendingOAuthReload(null);
    }
  }, [pendingOAuthReload, selectedCompanyId]);

  // Load connectors when company changes
  useEffect(() => {
    if (selectedCompanyId) {
      loadQbConnector();
      loadCvConnector();
    } else {
      // Reset QuickBooks state
      setQbConnector(null);
      setQbAvailableEntities([]);
      setQbSelectedEntities([]);
      setQbStats(null);
      setQbSyncLogs([]);
      // Reset Carbon Voice state
      setCvConnector(null);
      setCvAvailableEntities([]);
      setCvSelectedEntities([]);
      setCvStats(null);
      setCvSyncLogs([]);
    }
  }, [selectedCompanyId]);

  // QuickBooks load functions
  const loadQbConnector = async () => {
    if (!selectedCompanyId) return;

    try {
      setLoadingQbConnector(true);
      setError(null);
      const response = await quickbooksApi.list(selectedCompanyId);

      if (response.connectors && response.connectors.length > 0) {
        const connector = response.connectors[0];
        console.log('[Connectors] Loaded QuickBooks connector:', connector);
        setQbConnector(connector);
        setQbSelectedEntities(connector.enabled_entities || []);

        if (connector.connector_status === 'connected') {
          loadQbEntities(connector.id);
          loadQbStats(connector.id);
          loadQbSyncLogs(connector.id);
        }
      } else {
        setQbConnector(null);
        setQbAvailableEntities([]);
        setQbSelectedEntities([]);
        setQbStats(null);
        setQbSyncLogs([]);
      }
    } catch (err) {
      setQbConnector(null);
      setQbAvailableEntities([]);
      setQbSelectedEntities([]);
      setQbStats(null);
      setQbSyncLogs([]);
    } finally {
      setLoadingQbConnector(false);
    }
  };

  const loadQbEntities = async (connectorId: string, showRefreshHint: boolean = false) => {
    if (!connectorId) return;

    try {
      setLoadingQbEntities(true);
      setError(null);
      const response = await quickbooksApi.discoverEntities(connectorId, showRefreshHint);
      setQbAvailableEntities(response.entities || []);
    } catch (err) {
      console.error('Failed to load QuickBooks entities:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load entities from QuickBooks';
      setError(errorMessage);
    } finally {
      setLoadingQbEntities(false);
    }
  };

  const loadQbStats = async (connectorId: string) => {
    if (!connectorId) return;

    try {
      const connectorStats = await quickbooksApi.getStats(connectorId);
      setQbStats(connectorStats);
    } catch (err) {
      console.error('Failed to load QuickBooks stats:', err);
    }
  };

  const loadQbSyncLogs = async (connectorId: string) => {
    if (!connectorId) return;

    try {
      const response = await quickbooksApi.listSyncLogs(connectorId, 5);
      setQbSyncLogs(response.sync_logs || []);
    } catch (err) {
      console.error('Failed to load QuickBooks sync logs:', err);
    }
  };

  // Carbon Voice load functions
  const loadCvConnector = async () => {
    if (!selectedCompanyId) return;

    try {
      setLoadingCvConnector(true);
      setError(null);
      const response = await carbonvoiceApi.list(selectedCompanyId);

      if (response.connectors && response.connectors.length > 0) {
        const connector = response.connectors[0];
        console.log('[Connectors] Loaded Carbon Voice connector:', connector);
        setCvConnector(connector);
        setCvSelectedEntities(connector.enabled_entities || []);

        if (connector.connector_status === 'connected') {
          loadCvEntities(connector.id);
          loadCvStats(connector.id);
          loadCvSyncLogs(connector.id);
        }
      } else {
        setCvConnector(null);
        setCvAvailableEntities([]);
        setCvSelectedEntities([]);
        setCvStats(null);
        setCvSyncLogs([]);
      }
    } catch (err) {
      setCvConnector(null);
      setCvAvailableEntities([]);
      setCvSelectedEntities([]);
      setCvStats(null);
      setCvSyncLogs([]);
    } finally {
      setLoadingCvConnector(false);
    }
  };

  const loadCvEntities = async (connectorId: string, showRefreshHint: boolean = false) => {
    if (!connectorId) return;

    try {
      setLoadingCvEntities(true);
      setError(null);
      const response = await carbonvoiceApi.discoverEntities(connectorId, showRefreshHint);
      setCvAvailableEntities(response.entities || []);
    } catch (err) {
      console.error('Failed to load Carbon Voice entities:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load entities from Carbon Voice';
      setError(errorMessage);
    } finally {
      setLoadingCvEntities(false);
    }
  };

  const loadCvStats = async (connectorId: string) => {
    if (!connectorId) return;

    try {
      const connectorStats = await carbonvoiceApi.getStats(connectorId);
      setCvStats(connectorStats);
    } catch (err) {
      console.error('Failed to load Carbon Voice stats:', err);
    }
  };

  const loadCvSyncLogs = async (connectorId: string) => {
    if (!connectorId) return;

    try {
      const response = await carbonvoiceApi.listSyncLogs(connectorId, 5);
      setCvSyncLogs(response.sync_logs || []);
    } catch (err) {
      console.error('Failed to load Carbon Voice sync logs:', err);
    }
  };

  // Connect to QuickBooks
  const handleQbConnect = async () => {
    if (!selectedCompanyId) {
      setError('Please select a company first');
      return;
    }

    try {
      setConnectingQb(true);
      setError(null);
      const response = await quickbooksApi.startOAuth(selectedCompanyId);
      window.location.href = response.authorization_url;
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start OAuth flow';
      setError(errorMessage);
      setConnectingQb(false);
    }
  };

  // Connect to Carbon Voice
  const handleCvConnect = async () => {
    if (!selectedCompanyId) {
      setError('Please select a company first');
      return;
    }

    try {
      setConnectingCv(true);
      setError(null);
      const response = await carbonvoiceApi.startOAuth(selectedCompanyId);
      window.location.href = response.authorization_url;
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start OAuth flow';
      setError(errorMessage);
      setConnectingCv(false);
    }
  };

  // Disconnect handler
  const handleDisconnect = async () => {
    if (!showDisconnectModal) return;

    try {
      setDisconnecting(true);
      if (showDisconnectModal === 'quickbooks' && qbConnector?.id) {
        await quickbooksApi.disconnect(qbConnector.id);
        setQbConnector(null);
        setQbAvailableEntities([]);
        setQbSelectedEntities([]);
        setQbStats(null);
        setQbSyncLogs([]);
        setSuccess('QuickBooks disconnected successfully');
      } else if (showDisconnectModal === 'carbonvoice' && cvConnector?.id) {
        await carbonvoiceApi.disconnect(cvConnector.id);
        setCvConnector(null);
        setCvAvailableEntities([]);
        setCvSelectedEntities([]);
        setCvStats(null);
        setCvSyncLogs([]);
        setSuccess('Carbon Voice disconnected successfully');
      }
    } catch (err) {
      const connectorName = showDisconnectModal === 'carbonvoice' ? 'Carbon Voice' : 'QuickBooks';
      setError(`Failed to disconnect ${connectorName}`);
    } finally {
      setDisconnecting(false);
      setShowDisconnectModal(null);
    }
  };

  // QuickBooks entity handlers
  const handleSaveQbEntities = async () => {
    if (!qbConnector?.id) return;

    try {
      setSavingQbEntities(true);
      setError(null);
      await quickbooksApi.update(qbConnector.id, { enabled_entities: qbSelectedEntities });
      setSuccess('QuickBooks entity selection saved');
      loadQbConnector();
    } catch (err) {
      setError('Failed to save QuickBooks entity selection');
    } finally {
      setSavingQbEntities(false);
    }
  };

  const toggleQbEntity = (entityKey: string) => {
    setQbSelectedEntities((prev) =>
      prev.includes(entityKey) ? prev.filter((e) => e !== entityKey) : [...prev, entityKey]
    );
  };

  const selectAllQbEntities = () => {
    const availableKeys = qbAvailableEntities.filter((e) => e.is_available).map((e) => e.entity_key);
    setQbSelectedEntities(availableKeys);
  };

  const deselectAllQbEntities = () => {
    setQbSelectedEntities([]);
  };

  // Carbon Voice entity handlers
  const handleSaveCvEntities = async () => {
    if (!cvConnector?.id) return;

    try {
      setSavingCvEntities(true);
      setError(null);
      await carbonvoiceApi.update(cvConnector.id, { enabled_entities: cvSelectedEntities });
      setSuccess('Carbon Voice entity selection saved');
      loadCvConnector();
    } catch (err) {
      setError('Failed to save Carbon Voice entity selection');
    } finally {
      setSavingCvEntities(false);
    }
  };

  const toggleCvEntity = (entityKey: string) => {
    setCvSelectedEntities((prev) =>
      prev.includes(entityKey) ? prev.filter((e) => e !== entityKey) : [...prev, entityKey]
    );
  };

  const selectAllCvEntities = () => {
    const availableKeys = cvAvailableEntities.filter((e) => e.is_available).map((e) => e.entity_key);
    setCvSelectedEntities(availableKeys);
  };

  const deselectAllCvEntities = () => {
    setCvSelectedEntities([]);
  };

  // QuickBooks sync
  const handleQbSync = async (fullSync: boolean = true) => {
    if (!qbConnector?.id) return;

    try {
      setQbSyncState({ syncing: true, currentSyncId: null, progress: 'Starting sync...' });
      setError(null);

      const response = await quickbooksApi.startSync(qbConnector.id, {
        full_sync: fullSync,
        entities: qbSelectedEntities.length > 0 ? qbSelectedEntities : undefined,
      });

      setQbSyncState({ syncing: true, currentSyncId: response.sync_log_id, progress: 'Sync in progress...' });
      pollQbSyncStatus(qbConnector.id, response.sync_log_id);
    } catch (err) {
      setError('Failed to start QuickBooks sync');
      setQbSyncState({ syncing: false, currentSyncId: null, progress: '' });
    }
  };

  const pollQbSyncStatus = useCallback(async (connectorId: string, syncLogId: string) => {
    const poll = async () => {
      try {
        const status = await quickbooksApi.getSyncStatus(connectorId, syncLogId);

        if (status.status === 'completed') {
          setQbSyncState({ syncing: false, currentSyncId: null, progress: '' });
          setSuccess(`QuickBooks sync completed! ${status.total_records_fetched} records synced.`);
          loadQbStats(connectorId);
          loadQbSyncLogs(connectorId);
        } else if (status.status === 'failed') {
          setQbSyncState({ syncing: false, currentSyncId: null, progress: '' });
          setError(`QuickBooks sync failed: ${status.error_message || 'Unknown error'}`);
          loadQbSyncLogs(connectorId);
        } else {
          setQbSyncState((prev) => ({
            ...prev,
            progress: `Syncing... ${status.total_records_fetched} records processed`,
          }));
          setTimeout(poll, 2000);
        }
      } catch (err) {
        setQbSyncState({ syncing: false, currentSyncId: null, progress: '' });
        setError('Failed to get QuickBooks sync status');
      }
    };

    poll();
  }, []);

  // Carbon Voice sync
  const handleCvSync = async (fullSync: boolean = true) => {
    if (!cvConnector?.id) return;

    try {
      setCvSyncState({ syncing: true, currentSyncId: null, progress: 'Starting sync...' });
      setError(null);

      const response = await carbonvoiceApi.startSync(cvConnector.id, {
        full_sync: fullSync,
        entities: cvSelectedEntities.length > 0 ? cvSelectedEntities : undefined,
      });

      setCvSyncState({ syncing: true, currentSyncId: response.sync_log_id, progress: 'Sync in progress...' });
      pollCvSyncStatus(cvConnector.id, response.sync_log_id);
    } catch (err) {
      setError('Failed to start Carbon Voice sync');
      setCvSyncState({ syncing: false, currentSyncId: null, progress: '' });
    }
  };

  const pollCvSyncStatus = useCallback(async (connectorId: string, syncLogId: string) => {
    const poll = async () => {
      try {
        const status = await carbonvoiceApi.getSyncStatus(connectorId, syncLogId);

        if (status.status === 'completed') {
          setCvSyncState({ syncing: false, currentSyncId: null, progress: '' });
          setSuccess(`Carbon Voice sync completed! ${status.total_records_fetched} records synced.`);
          loadCvStats(connectorId);
          loadCvSyncLogs(connectorId);
        } else if (status.status === 'failed') {
          setCvSyncState({ syncing: false, currentSyncId: null, progress: '' });
          setError(`Carbon Voice sync failed: ${status.error_message || 'Unknown error'}`);
          loadCvSyncLogs(connectorId);
        } else {
          setCvSyncState((prev) => ({
            ...prev,
            progress: `Syncing... ${status.total_records_fetched} records processed`,
          }));
          setTimeout(poll, 2000);
        }
      } catch (err) {
        setCvSyncState({ syncing: false, currentSyncId: null, progress: '' });
        setError('Failed to get Carbon Voice sync status');
      }
    };

    poll();
  }, []);

  // QuickBooks ingestion
  const handleQbIngestion = async () => {
    if (!qbConnector?.id) return;

    try {
      setQbIngestionState({
        isProcessing: true,
        connectorConfigId: qbConnector.id,
        step: 1,
        stepName: 'Queuing...',
        progress: 0,
        currentEntity: null,
        entitiesCompleted: [],
        recordsProcessed: 0,
        chunksCreated: 0,
      });
      setError(null);

      const result = await quickbooksApi.runIngestion(qbConnector.id);

      if (result.status === 'queued') {
        setQbIngestionState((prev) => ({
          ...prev,
          stepName: 'Queued - waiting for processing...',
        }));
      }
    } catch (err) {
      setError('Failed to queue QuickBooks ingestion');
      setQbIngestionState((prev) => ({
        ...prev,
        isProcessing: false,
      }));
    }
  };

  // Carbon Voice ingestion
  const handleCvIngestion = async () => {
    if (!cvConnector?.id) return;

    try {
      setCvIngestionState({
        isProcessing: true,
        connectorConfigId: cvConnector.id,
        step: 1,
        stepName: 'Queuing...',
        progress: 0,
        currentEntity: null,
        entitiesCompleted: [],
        recordsProcessed: 0,
        chunksCreated: 0,
      });
      setError(null);

      const result = await carbonvoiceApi.runIngestion(cvConnector.id);

      if (result.status === 'queued') {
        setCvIngestionState((prev) => ({
          ...prev,
          stepName: 'Queued - waiting for processing...',
        }));
      }
    } catch (err) {
      setError('Failed to queue Carbon Voice ingestion');
      setCvIngestionState((prev) => ({
        ...prev,
        isProcessing: false,
      }));
    }
  };

  // Clear messages after timeout
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 10000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  // Render status badge
  const renderStatusBadge = (status: ConnectionStatus) => {
    const statusClasses: Record<ConnectionStatus, string> = {
      connected: styles.statusConnected,
      disconnected: styles.statusDisconnected,
      expired: styles.statusExpired,
      error: styles.statusError,
    };

    return <span className={`${styles.statusBadge} ${statusClasses[status]}`}>{status}</span>;
  };

  // Render sync status badge
  const renderSyncStatusBadge = (status: string) => {
    const statusClasses: Record<string, string> = {
      completed: styles.syncStatusCompleted,
      failed: styles.syncStatusFailed,
      in_progress: styles.syncStatusRunning,
      pending: styles.syncStatusPending,
    };

    return <span className={`${styles.syncStatusBadge} ${statusClasses[status] || ''}`}>{status}</span>;
  };

  return (
    <AppLayout title="Connectors" subtitle="Manage external data integrations">
      <div className={styles.container}>
        {/* Messages */}
        {error && <div className={styles.errorMessage}>{error}</div>}
        {success && <div className={styles.successMessage}>{success}</div>}

        {/* No company selected message */}
        {!selectedCompanyId && (
          <div className={styles.card}>
            <p className={styles.connectorDescription}>
              Please select a company from the sidebar to manage connectors.
            </p>
          </div>
        )}

        {/* Connectors Grid */}
        {selectedCompanyId && (
          <div className={styles.connectorsGrid}>
            {/* Render unavailable connectors as preview cards */}
            {AVAILABLE_CONNECTORS.filter(c => !c.isAvailable).map((connectorDef) => (
              <div
                key={connectorDef.id}
                className={styles.connectorPreviewCard}
              >
                <div className={styles.previewCardContent}>
                  <div className={`${styles.connectorIcon} ${connectorDef.iconClass}`}>
                    {connectorDef.shortName}
                  </div>
                  <h3 className={styles.previewCardTitle}>{connectorDef.name}</h3>
                  <p className={styles.previewCardDescription}>{connectorDef.description}</p>
                  <div className={styles.previewCardFeatures}>
                    {connectorDef.features.map((feature) => (
                      <span key={feature} className={styles.featureTag}>{feature}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}

            {/* QuickBooks Connector Card */}
            <div className={`${styles.card} ${qbConnector && qbConnector.connector_status === 'connected' ? styles.expandedCard : ''}`}>
              <div className={styles.connectorHeader}>
                <div className={styles.connectorInfo}>
                  <div className={styles.connectorIcon}>QB</div>
                  <div>
                    <h2 className={styles.cardTitle}>QuickBooks Online</h2>
                    <p className={styles.connectorDescription}>
                      Connect to QuickBooks Online for financial data
                    </p>
                  </div>
                </div>
                {qbConnector && renderStatusBadge(qbConnector.connector_status)}
              </div>

              {loadingQbConnector ? (
                <div className={styles.loadingSection}>
                  <Loader size="medium" text="Loading connector..." />
                </div>
              ) : qbConnector && qbConnector.connector_status === 'connected' ? (
                <div className={styles.connectorContent}>
                  <div className={styles.connectionInfo}>
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>QuickBooks Company</span>
                      <span className={styles.infoValue}>{qbConnector.external_company_name || 'N/A'}</span>
                    </div>
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>QuickBooks ID</span>
                      <span className={styles.infoValue}>{qbConnector.external_company_id || 'N/A'}</span>
                    </div>
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>Last Sync</span>
                      <span className={styles.infoValue}>
                        {qbConnector.last_sync_at ? new Date(qbConnector.last_sync_at).toLocaleString() : 'Never'}
                      </span>
                    </div>
                  </div>

                  {qbStats && (
                    <div className={styles.statsGrid}>
                      <div className={styles.statCard}>
                        <div className={styles.statValue}>{qbStats.raw_data_records}</div>
                        <div className={styles.statLabel}>Raw Records</div>
                      </div>
                      <div className={styles.statCard}>
                        <div className={styles.statValue}>{qbStats.chunks_created}</div>
                        <div className={styles.statLabel}>Processed Chunks</div>
                      </div>
                      <div className={styles.statCard}>
                        <div className={styles.statValue}>{qbStats.sync_operations}</div>
                        <div className={styles.statLabel}>Sync Operations</div>
                      </div>
                    </div>
                  )}

                  <div className={styles.entitySection}>
                    <div className={styles.entityHeader}>
                      <h3 className={styles.sectionTitle}>Data Entities</h3>
                      <div className={styles.entityActions}>
                        <button onClick={selectAllQbEntities} className={styles.textButton} disabled={loadingQbEntities}>Select All</button>
                        <button onClick={deselectAllQbEntities} className={styles.textButton} disabled={loadingQbEntities}>Deselect All</button>
                        <button onClick={() => qbConnector?.id && loadQbEntities(qbConnector.id, true)} className={styles.textButton} disabled={loadingQbEntities}>Refresh</button>
                      </div>
                    </div>

                    {loadingQbEntities ? (
                      <Loader size="small" text="Loading entities..." />
                    ) : qbAvailableEntities.length > 0 ? (
                      <div className={styles.entityGrid}>
                        {qbAvailableEntities.map((entity) => (
                          <label key={entity.entity_key} className={`${styles.entityCard} ${!entity.is_available ? styles.entityDisabled : ''}`}>
                            <input type="checkbox" checked={qbSelectedEntities.includes(entity.entity_key)} onChange={() => toggleQbEntity(entity.entity_key)} disabled={!entity.is_available} className={styles.entityCheckbox} />
                            <div className={styles.entityInfo}>
                              <div className={styles.entityName}>{entity.display_name}</div>
                              <div className={styles.entityDescription}>{entity.description}</div>
                              {entity.record_count !== null && <div className={styles.entityCount}>{entity.record_count} records</div>}
                            </div>
                          </label>
                        ))}
                      </div>
                    ) : (
                      <p className={styles.syncHint}>No entities discovered yet. Click Refresh to load.</p>
                    )}

                    <div className={styles.entityFooter}>
                      <button onClick={handleSaveQbEntities} className={styles.primaryButton} disabled={savingQbEntities}>
                        {savingQbEntities ? 'Saving...' : 'Save Selection'}
                      </button>
                    </div>
                  </div>

                  <div className={styles.syncSection}>
                    <h3 className={styles.sectionTitle}>Sync Data</h3>
                    {qbSyncState.syncing ? (
                      <div className={styles.syncProgress}><Loader size="small" /><span>{qbSyncState.progress}</span></div>
                    ) : (
                      <div className={styles.syncActions}>
                        <button onClick={() => handleQbSync(true)} className={styles.primaryButton} disabled={qbSelectedEntities.length === 0}>Full Sync</button>
                        <button onClick={() => handleQbSync(false)} className={styles.secondaryButton} disabled={qbSelectedEntities.length === 0 || !qbConnector.last_sync_at}>Delta Sync</button>
                      </div>
                    )}
                    {qbSelectedEntities.length === 0 && <p className={styles.syncHint}>Select at least one entity to sync</p>}
                  </div>

                  <div className={styles.ingestionSection}>
                    <h3 className={styles.sectionTitle}>Process Data</h3>
                    <p className={styles.sectionDescription}>Run ingestion to process synced data into searchable chunks.</p>
                    {qbIngestionState.isProcessing ? (
                      <div className={styles.ingestionProgress}>
                        <div className={styles.progressContainer}>
                          <div className={styles.progressBar}><div className={styles.progressFill} style={{ width: `${qbIngestionState.progress}%` }} /></div>
                          <div className={styles.progressSteps}>
                            {INGESTION_STEPS.map((step) => {
                              const currentStep = qbIngestionState.step || 0;
                              const isCompleted = currentStep > step.step;
                              const isActive = currentStep === step.step;
                              return <span key={step.step} className={`${styles.progressStep} ${isCompleted ? styles.progressStepCompleted : ''} ${isActive ? styles.progressStepActive : ''}`}>{isCompleted ? '✓' : isActive ? '→' : '○'} {step.name}</span>;
                            })}
                          </div>
                        </div>
                        <div className={styles.ingestionDetails}>
                          <span className={styles.ingestionStep}>{qbIngestionState.stepName}{qbIngestionState.currentEntity && ` - ${qbIngestionState.currentEntity}`}</span>
                          <span className={styles.ingestionStats}>{qbIngestionState.recordsProcessed > 0 && `${qbIngestionState.recordsProcessed} records`}{qbIngestionState.chunksCreated > 0 && ` | ${qbIngestionState.chunksCreated} chunks`}</span>
                        </div>
                      </div>
                    ) : (
                      <div className={styles.ingestionActions}>
                        <button onClick={handleQbIngestion} className={styles.primaryButton} disabled={(qbStats?.raw_data_records || 0) === 0}>Run Ingestion</button>
                        {qbIngestionState.chunksCreated > 0 && qbIngestionState.step === 6 && <span className={styles.ingestionResult}>{qbIngestionState.chunksCreated} chunks created</span>}
                      </div>
                    )}
                    {(qbStats?.raw_data_records || 0) === 0 && !qbIngestionState.isProcessing && <p className={styles.syncHint}>Sync data first before running ingestion</p>}
                  </div>

                  {qbSyncLogs.length > 0 && (
                    <div className={styles.syncHistorySection}>
                      <h3 className={styles.sectionTitle}>Sync History</h3>
                      <div className={styles.syncHistoryTable}>
                        <table>
                          <thead><tr><th>Date</th><th>Type</th><th>Status</th><th>Records</th></tr></thead>
                          <tbody>
                            {qbSyncLogs.map((log) => (
                              <tr key={log.id}>
                                <td>{log.started_at ? new Date(log.started_at).toLocaleString() : 'Pending'}</td>
                                <td>{log.sync_type}</td>
                                <td>{renderSyncStatusBadge(log.sync_status)}</td>
                                <td>{log.total_records_fetched}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className={styles.disconnectSection}>
                    <button onClick={() => setShowDisconnectModal('quickbooks')} className={styles.dangerButton}>Disconnect QuickBooks</button>
                  </div>
                </div>
              ) : (
                <div className={styles.notConnected}>
                  <p className={styles.notConnectedText}>QuickBooks is not connected for this company. Connect to sync financial data.</p>
                  <button onClick={handleQbConnect} className={styles.primaryButton} disabled={connectingQb}>{connectingQb ? 'Connecting...' : 'Connect QuickBooks'}</button>
                </div>
              )}
            </div>

            {/* Carbon Voice Connector Card */}
            <div className={`${styles.card} ${cvConnector && cvConnector.connector_status === 'connected' ? styles.expandedCard : ''}`}>
              <div className={styles.connectorHeader}>
                <div className={styles.connectorInfo}>
                  <div className={`${styles.connectorIcon} ${styles.connectorIconCarbonVoice}`}>CV</div>
                  <div>
                    <h2 className={styles.cardTitle}>Carbon Voice</h2>
                    <p className={styles.connectorDescription}>
                      Connect to Carbon Voice for conversation and action item data
                    </p>
                  </div>
                </div>
                {cvConnector && renderStatusBadge(cvConnector.connector_status)}
              </div>

              {loadingCvConnector ? (
                <div className={styles.loadingSection}>
                  <Loader size="medium" text="Loading connector..." />
                </div>
              ) : cvConnector && cvConnector.connector_status === 'connected' ? (
                <div className={styles.connectorContent}>
                  <div className={styles.connectionInfo}>
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>Carbon Voice Account</span>
                      <span className={styles.infoValue}>{cvConnector.external_company_name || 'N/A'}</span>
                    </div>
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>Account ID</span>
                      <span className={styles.infoValue}>{cvConnector.external_company_id || 'N/A'}</span>
                    </div>
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>Last Sync</span>
                      <span className={styles.infoValue}>
                        {cvConnector.last_sync_at ? new Date(cvConnector.last_sync_at).toLocaleString() : 'Never'}
                      </span>
                    </div>
                  </div>

                  {cvStats && (
                    <div className={styles.statsGrid}>
                      <div className={styles.statCard}>
                        <div className={styles.statValue}>{cvStats.raw_data_records}</div>
                        <div className={styles.statLabel}>Raw Records</div>
                      </div>
                      <div className={styles.statCard}>
                        <div className={styles.statValue}>{cvStats.chunks_created}</div>
                        <div className={styles.statLabel}>Processed Chunks</div>
                      </div>
                      <div className={styles.statCard}>
                        <div className={styles.statValue}>{cvStats.sync_operations}</div>
                        <div className={styles.statLabel}>Sync Operations</div>
                      </div>
                    </div>
                  )}

                  <div className={styles.entitySection}>
                    <div className={styles.entityHeader}>
                      <h3 className={styles.sectionTitle}>Data Entities</h3>
                      <div className={styles.entityActions}>
                        <button onClick={selectAllCvEntities} className={styles.textButton} disabled={loadingCvEntities}>Select All</button>
                        <button onClick={deselectAllCvEntities} className={styles.textButton} disabled={loadingCvEntities}>Deselect All</button>
                        <button onClick={() => cvConnector?.id && loadCvEntities(cvConnector.id, true)} className={styles.textButton} disabled={loadingCvEntities}>Refresh</button>
                      </div>
                    </div>

                    {loadingCvEntities ? (
                      <Loader size="small" text="Loading entities..." />
                    ) : cvAvailableEntities.length > 0 ? (
                      <div className={styles.entityGrid}>
                        {cvAvailableEntities.map((entity) => (
                          <label key={entity.entity_key} className={`${styles.entityCard} ${!entity.is_available ? styles.entityDisabled : ''}`}>
                            <input type="checkbox" checked={cvSelectedEntities.includes(entity.entity_key)} onChange={() => toggleCvEntity(entity.entity_key)} disabled={!entity.is_available} className={styles.entityCheckbox} />
                            <div className={styles.entityInfo}>
                              <div className={styles.entityName}>{entity.display_name}</div>
                              <div className={styles.entityDescription}>{entity.description}</div>
                              {entity.record_count !== null && <div className={styles.entityCount}>{entity.record_count} records</div>}
                            </div>
                          </label>
                        ))}
                      </div>
                    ) : (
                      <p className={styles.syncHint}>No entities discovered yet. Click Refresh to load.</p>
                    )}

                    <div className={styles.entityFooter}>
                      <button onClick={handleSaveCvEntities} className={styles.primaryButton} disabled={savingCvEntities}>
                        {savingCvEntities ? 'Saving...' : 'Save Selection'}
                      </button>
                    </div>
                  </div>

                  <div className={styles.syncSection}>
                    <h3 className={styles.sectionTitle}>Sync Data</h3>
                    {cvSyncState.syncing ? (
                      <div className={styles.syncProgress}><Loader size="small" /><span>{cvSyncState.progress}</span></div>
                    ) : (
                      <div className={styles.syncActions}>
                        <button onClick={() => handleCvSync(true)} className={styles.primaryButton} disabled={cvSelectedEntities.length === 0}>Full Sync</button>
                        <button onClick={() => handleCvSync(false)} className={styles.secondaryButton} disabled={cvSelectedEntities.length === 0 || !cvConnector.last_sync_at}>Delta Sync</button>
                      </div>
                    )}
                    {cvSelectedEntities.length === 0 && <p className={styles.syncHint}>Select at least one entity to sync</p>}
                  </div>

                  <div className={styles.ingestionSection}>
                    <h3 className={styles.sectionTitle}>Process Data</h3>
                    <p className={styles.sectionDescription}>Run ingestion to process synced data into searchable chunks.</p>
                    {cvIngestionState.isProcessing ? (
                      <div className={styles.ingestionProgress}>
                        <div className={styles.progressContainer}>
                          <div className={styles.progressBar}><div className={styles.progressFill} style={{ width: `${cvIngestionState.progress}%` }} /></div>
                          <div className={styles.progressSteps}>
                            {INGESTION_STEPS.map((step) => {
                              const currentStep = cvIngestionState.step || 0;
                              const isCompleted = currentStep > step.step;
                              const isActive = currentStep === step.step;
                              return <span key={step.step} className={`${styles.progressStep} ${isCompleted ? styles.progressStepCompleted : ''} ${isActive ? styles.progressStepActive : ''}`}>{isCompleted ? '✓' : isActive ? '→' : '○'} {step.name}</span>;
                            })}
                          </div>
                        </div>
                        <div className={styles.ingestionDetails}>
                          <span className={styles.ingestionStep}>{cvIngestionState.stepName}{cvIngestionState.currentEntity && ` - ${cvIngestionState.currentEntity}`}</span>
                          <span className={styles.ingestionStats}>{cvIngestionState.recordsProcessed > 0 && `${cvIngestionState.recordsProcessed} records`}{cvIngestionState.chunksCreated > 0 && ` | ${cvIngestionState.chunksCreated} chunks`}</span>
                        </div>
                      </div>
                    ) : (
                      <div className={styles.ingestionActions}>
                        <button onClick={handleCvIngestion} className={styles.primaryButton} disabled={(cvStats?.raw_data_records || 0) === 0}>Run Ingestion</button>
                        {cvIngestionState.chunksCreated > 0 && cvIngestionState.step === 6 && <span className={styles.ingestionResult}>{cvIngestionState.chunksCreated} chunks created</span>}
                      </div>
                    )}
                    {(cvStats?.raw_data_records || 0) === 0 && !cvIngestionState.isProcessing && <p className={styles.syncHint}>Sync data first before running ingestion</p>}
                  </div>

                  {cvSyncLogs.length > 0 && (
                    <div className={styles.syncHistorySection}>
                      <h3 className={styles.sectionTitle}>Sync History</h3>
                      <div className={styles.syncHistoryTable}>
                        <table>
                          <thead><tr><th>Date</th><th>Type</th><th>Status</th><th>Records</th></tr></thead>
                          <tbody>
                            {cvSyncLogs.map((log) => (
                              <tr key={log.id}>
                                <td>{log.started_at ? new Date(log.started_at).toLocaleString() : 'Pending'}</td>
                                <td>{log.sync_type}</td>
                                <td>{renderSyncStatusBadge(log.sync_status)}</td>
                                <td>{log.total_records_fetched}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className={styles.disconnectSection}>
                    <button onClick={() => setShowDisconnectModal('carbonvoice')} className={styles.dangerButton}>Disconnect Carbon Voice</button>
                  </div>
                </div>
              ) : (
                <div className={styles.notConnected}>
                  <p className={styles.notConnectedText}>Carbon Voice is not connected for this company. Connect to sync conversation data.</p>
                  <button onClick={handleCvConnect} className={styles.primaryButton} disabled={connectingCv}>{connectingCv ? 'Connecting...' : 'Connect Carbon Voice'}</button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Disconnect Confirmation Modal */}
        <ConfirmModal
          isOpen={showDisconnectModal !== null}
          type="danger"
          title={`Disconnect ${showDisconnectModal === 'carbonvoice' ? 'Carbon Voice' : 'QuickBooks'}`}
          message={`Are you sure you want to disconnect ${showDisconnectModal === 'carbonvoice' ? 'Carbon Voice' : 'QuickBooks'}? This will remove all synced data and chunks. This action cannot be undone.`}
          confirmText={disconnecting ? 'Disconnecting...' : 'Disconnect'}
          cancelText="Cancel"
          isLoading={disconnecting}
          onConfirm={handleDisconnect}
          onCancel={() => setShowDisconnectModal(null)}
        />
      </div>
    </AppLayout>
  );
}
