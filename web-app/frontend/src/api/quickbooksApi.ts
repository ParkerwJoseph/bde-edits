import { api } from '../utils/api';

// Types matching backend schemas
export interface ConnectorConfig {
  id: string;
  tenant_id: string;
  company_id: string;
  connector_type: 'quickbooks';
  connector_status: 'connected' | 'disconnected' | 'expired' | 'error';
  external_company_id: string | null;
  external_company_name: string | null;
  available_entities: Record<string, EntityInfo> | null;
  enabled_entities: string[] | null;
  sync_settings: Record<string, unknown> | null;
  last_sync_at: string | null;
  last_sync_status: 'pending' | 'in_progress' | 'completed' | 'failed' | null;
  last_sync_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectorListResponse {
  connectors: ConnectorConfig[];
  total: number;
}

export interface EntityInfo {
  entity_key: string;
  display_name: string;
  description: string;
  is_report: boolean;
  default_enabled: boolean;
  pillar_hint: string;
  record_count: number | null;
  is_available: boolean;
  error: string | null;
}

export interface DiscoverEntitiesResponse {
  entities: EntityInfo[];
  company_info: Record<string, unknown> | null;
}

export interface OAuthStartResponse {
  authorization_url: string;
  state: string;
}

export interface SyncLog {
  id: string;
  connector_config_id: string;
  sync_status: 'pending' | 'in_progress' | 'completed' | 'failed';
  sync_type: string;
  entities_requested: string[] | null;
  entities_completed: string[] | null;
  total_records_fetched: number;
  total_records_processed: number;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface SyncLogListResponse {
  sync_logs: SyncLog[];
  total: number;
}

export interface SyncStartResponse {
  sync_log_id: string;
  status: string;
  message: string;
}

export interface SyncStatusResponse {
  id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  sync_type: string;
  entities_requested: string[] | null;
  entities_completed: string[] | null;
  total_records_fetched: number;
  total_records_processed: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface ConnectorStats {
  connector_id: string;
  connector_type: string;
  connector_status: string;
  external_company_name: string | null;
  raw_data_records: number;
  unprocessed_records: number;
  processed_records: number;
  chunks_created: number;
  sync_operations: number;
  last_sync_at: string | null;
  last_sync_status: string | null;
}

export interface QuickBooksInfo {
  connector_type: string;
  display_name: string;
  description: string;
  is_configured: boolean;
}

export const quickbooksApi = {
  /**
   * Get QuickBooks connector information
   */
  getInfo: async (): Promise<QuickBooksInfo> => {
    const response = await api.get<QuickBooksInfo>('/api/connectors/quickbooks/info');
    return response.data;
  },

  /**
   * List all QuickBooks connectors for a company
   */
  list: async (companyId: string): Promise<ConnectorListResponse> => {
    const response = await api.get<ConnectorListResponse>('/api/connectors/quickbooks/', {
      params: { company_id: companyId },
    });
    return response.data;
  },

  /**
   * Get a specific connector configuration
   */
  get: async (connectorId: string): Promise<ConnectorConfig> => {
    const response = await api.get<ConnectorConfig>(`/api/connectors/quickbooks/${connectorId}`);
    return response.data;
  },

  /**
   * Update connector configuration (e.g., enabled entities)
   */
  update: async (connectorId: string, data: { enabled_entities?: string[] }): Promise<ConnectorConfig> => {
    const response = await api.patch<ConnectorConfig>(`/api/connectors/quickbooks/${connectorId}`, data);
    return response.data;
  },

  /**
   * Disconnect/delete a connector
   */
  disconnect: async (connectorId: string): Promise<void> => {
    await api.delete(`/api/connectors/quickbooks/${connectorId}`);
  },

  /**
   * Start OAuth flow - returns URL to redirect user to
   */
  startOAuth: async (companyId: string): Promise<OAuthStartResponse> => {
    const response = await api.post<OAuthStartResponse>('/api/connectors/quickbooks/oauth/start', null, {
      params: { company_id: companyId },
    });
    return response.data;
  },

  /**
   * Discover available entities from QuickBooks
   */
  discoverEntities: async (connectorId: string, refresh: boolean = false): Promise<DiscoverEntitiesResponse> => {
    const response = await api.get<DiscoverEntitiesResponse>(`/api/connectors/quickbooks/${connectorId}/entities`, {
      params: { refresh },
    });
    return response.data;
  },

  /**
   * Start a sync operation
   */
  startSync: async (
    connectorId: string,
    options?: { full_sync?: boolean; entities?: string[] }
  ): Promise<SyncStartResponse> => {
    const response = await api.post<SyncStartResponse>(
      `/api/connectors/quickbooks/${connectorId}/sync`,
      options || {}
    );
    return response.data;
  },

  /**
   * Get sync status
   */
  getSyncStatus: async (connectorId: string, syncLogId: string): Promise<SyncStatusResponse> => {
    const response = await api.get<SyncStatusResponse>(
      `/api/connectors/quickbooks/${connectorId}/sync/${syncLogId}`
    );
    return response.data;
  },

  /**
   * List sync logs for a connector
   */
  listSyncLogs: async (connectorId: string, limit?: number): Promise<SyncLogListResponse> => {
    const response = await api.get<SyncLogListResponse>(
      `/api/connectors/quickbooks/${connectorId}/sync-logs`,
      { params: { limit: limit || 10 } }
    );
    return response.data;
  },

  /**
   * Process synced data (run ingestion)
   * Returns immediately with connector_config_id - progress is tracked via WebSocket
   */
  runIngestion: async (connectorId: string, entityTypes?: string[]): Promise<{
    connector_config_id: string;
    status: string;
    message: string;
  }> => {
    const response = await api.post<{
      connector_config_id: string;
      status: string;
      message: string;
    }>(
      `/api/connectors/quickbooks/${connectorId}/ingest`,
      { entity_types: entityTypes || null }
    );
    return response.data;
  },

  /**
   * Get connector stats
   */
  getStats: async (connectorId: string): Promise<ConnectorStats> => {
    const response = await api.get<ConnectorStats>(`/api/connectors/quickbooks/${connectorId}/stats`);
    return response.data;
  },
};
