import { api } from '../utils/api';

// Types for BDE Scoring System
export type HealthStatus = 'green' | 'yellow' | 'red';
export type FlagType = 'red' | 'yellow' | 'green';
export type BDEPillar =
  | 'financial_health'
  | 'gtm_engine'
  | 'customer_health'
  | 'product_technical'
  | 'operational_maturity'
  | 'leadership_transition'
  | 'ecosystem_dependency'
  | 'service_software_ratio';

// Pillar metadata
export const PILLAR_CONFIG: Record<BDEPillar, { label: string; weight: number; color: string }> = {
  financial_health: { label: 'Financial Health', weight: 0.20, color: '#22c55e' },
  gtm_engine: { label: 'GTM Engine', weight: 0.15, color: '#3b82f6' },
  customer_health: { label: 'Customer Health', weight: 0.15, color: '#f59e0b' },
  product_technical: { label: 'Product/Technical', weight: 0.15, color: '#8b5cf6' },
  operational_maturity: { label: 'Operational Maturity', weight: 0.10, color: '#ec4899' },
  leadership_transition: { label: 'Leadership Transition', weight: 0.10, color: '#f97316' },
  ecosystem_dependency: { label: 'Ecosystem Dependency', weight: 0.10, color: '#06b6d4' },
  service_software_ratio: { label: 'Service/Software Ratio', weight: 0.05, color: '#84cc16' },
};

// Response types
export interface PillarScore {
  score: number;
  health_status: HealthStatus;
  confidence: number;
  data_coverage: number;
}

export interface BDEScoreResponse {
  company_id: string;
  overall_score: number;
  weighted_raw_score: number;
  valuation_range: string;
  confidence: number;
  calculated_at: string;
  pillar_scores: Record<BDEPillar, PillarScore>;
}

export interface PillarDetailResponse {
  pillar: string;
  score: number;
  health_status: HealthStatus;
  justification: string;
  data_coverage_percent: number;
  confidence: number;
  key_findings: string[];
  risks: string[];
  data_gaps: string[];
  evidence_chunk_ids: string[];
}

export interface MetricValue {
  numeric: number | null;
  text: string | null;
  json: unknown | null;  // For JSON array/object data (lists, tables)
  unit: string | null;
  period: string | null;
  as_of_date: string | null;
  confidence: number;
  is_current: boolean;
}

export interface Metric {
  current_value: MetricValue;
  pillars_used_by: string[];
  primary_pillar: string;
}

export interface MetricConflict {
  metric_name: string;
  value: string;
  period: string;
  confidence: number;
}

export interface MetricsResponse {
  metrics: Record<string, Metric>;
  conflicts: MetricConflict[];
}

export interface Flag {
  text: string;
  category: string;
  pillar: string;
  severity: number;
  source: string;
  rationale: string;
}

export interface FlagsResponse {
  red_flags: Flag[];
  yellow_flags: Flag[];
  green_accelerants: Flag[];
}

export interface RecommendationResponse {
  recommendation: string;
  confidence: number;
  rationale: string;
  value_drivers: string[];
  key_risks: string[];
  '100_day_plan': string[];
  suggested_valuation_multiple: number | null;
  valuation_adjustments: Record<string, number> | null;
  generated_at: string;
}

export interface ScoreCompanyResponse {
  status: string;
  message: string;
  company_id: string;
  job_started: boolean;
}

// Analysis status types
export interface AnalysisStatusResponse {
  company_id: string;
  has_score: boolean;
  is_running: boolean;
  last_scored_at: string | null;
  document_count: number;
  last_scored_doc_count: number;
  has_new_documents: boolean;
  has_new_connector_data: boolean;
  connector_count: number;
  can_run_analysis: boolean;
  message: string;
}

export interface DocumentCountResponse {
  company_id: string;
  total_documents: number;
  processed_documents: number;
  last_scored_at: string | null;
  last_scored_doc_count: number;
  has_new_documents: boolean;
}

// WebSocket progress types
export interface PillarProgressItem {
  name: string;
  status: 'pending' | 'processing' | 'completed';
  progress: number;
  score: number | null;
  health_status: HealthStatus | null;
}

export interface ScoringProgressMessage {
  type: 'scoring_progress' | 'ping';
  company_id?: string;
  stage?: number;
  stage_name?: string;
  progress?: number;
  status?: 'processing' | 'completed' | 'failed';
  current_pillar?: string | null;
  pillar_progress?: Record<string, PillarProgressItem>;
  error_message?: string | null;
  result?: {
    overall_score: number;
    valuation_range: string;
    confidence: number;
  } | null;
}

// Source document types for data lineage
export interface SourceDocumentInfo {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  document_type: string | null;
  document_title: string | null;
  status: string;
  total_pages: number | null;
  updated_at: string;
  metrics_count: number;
  chunks_count: number;
  confidence: number;
}

export interface DataSourcesResponse {
  documents: SourceDocumentInfo[];
  total_metrics: number;
  total_chunks: number;
}

export interface MetricSourceDocument {
  document_id: string;
  filename: string;
  page_numbers: number[];
}

// Generic source info - can be document or connector
export interface MetricSourceInfo {
  source_type: 'document' | 'connector';
  source_id: string;
  source_name: string;
  // Document-specific
  page_numbers?: number[];
  // Connector-specific
  connector_type?: string;
  entity_type?: string;
  entity_name?: string;
}

export interface MetricWithSource {
  current_value: MetricValue;
  pillars_used_by: string[];
  primary_pillar: string;
  source_documents: MetricSourceDocument[];  // Legacy
  sources: MetricSourceInfo[];  // New unified format
}

export interface MetricsWithSourcesResponse {
  metrics: Record<string, MetricWithSource>;
  conflicts: MetricConflict[];
  source_documents: SourceDocumentInfo[];
}

// API functions
export const scoringApi = {
  /**
   * Trigger scoring pipeline for a company
   */
  triggerScoring: async (companyId: string): Promise<ScoreCompanyResponse> => {
    const response = await api.post<ScoreCompanyResponse>(
      `/api/scoring/companies/${companyId}/score`,
      {}
    );
    return response.data;
  },

  /**
   * Get BDE score for a company
   */
  getBDEScore: async (companyId: string): Promise<BDEScoreResponse> => {
    const response = await api.get<BDEScoreResponse>(
      `/api/scoring/companies/${companyId}/bde-score`
    );
    return response.data;
  },

  /**
   * Get detailed pillar score
   */
  getPillarDetail: async (companyId: string, pillar: BDEPillar): Promise<PillarDetailResponse> => {
    const response = await api.get<PillarDetailResponse>(
      `/api/scoring/companies/${companyId}/pillars/${pillar}`
    );
    return response.data;
  },

  /**
   * Get all extracted metrics for a company
   */
  getMetrics: async (companyId: string): Promise<MetricsResponse> => {
    const response = await api.get<MetricsResponse>(
      `/api/scoring/companies/${companyId}/metrics`
    );
    return response.data;
  },

  /**
   * Get all flags for a company
   */
  getFlags: async (companyId: string): Promise<FlagsResponse> => {
    const response = await api.get<FlagsResponse>(
      `/api/scoring/companies/${companyId}/flags`
    );
    return response.data;
  },

  /**
   * Get acquisition recommendation for a company
   */
  getRecommendation: async (companyId: string): Promise<RecommendationResponse> => {
    const response = await api.get<RecommendationResponse>(
      `/api/scoring/companies/${companyId}/recommendation`
    );
    return response.data;
  },

  /**
   * Get all source documents for a company with metrics counts
   */
  getDataSources: async (companyId: string): Promise<DataSourcesResponse> => {
    const response = await api.get<DataSourcesResponse>(
      `/api/scoring/companies/${companyId}/data-sources`
    );
    return response.data;
  },

  /**
   * Get all metrics with source document information for data lineage
   */
  getMetricsWithSources: async (companyId: string): Promise<MetricsWithSourcesResponse> => {
    const response = await api.get<MetricsWithSourcesResponse>(
      `/api/scoring/companies/${companyId}/metrics-with-sources`
    );
    return response.data;
  },

  /**
   * Get analysis status for a company (can run, has new docs, etc.)
   */
  getAnalysisStatus: async (companyId: string): Promise<AnalysisStatusResponse> => {
    const response = await api.get<AnalysisStatusResponse>(
      `/api/scoring/companies/${companyId}/analysis-status`
    );
    return response.data;
  },

  /**
   * Get document count for a company
   */
  getDocumentCount: async (companyId: string): Promise<DocumentCountResponse> => {
    const response = await api.get<DocumentCountResponse>(
      `/api/scoring/companies/${companyId}/document-count`
    );
    return response.data;
  },
};

// Helper functions
export function getHealthStatusColor(status: HealthStatus): string {
  switch (status) {
    case 'green': return '#22c55e';
    case 'yellow': return '#f59e0b';
    case 'red': return '#ef4444';
    default: return '#6b7280';
  }
}

export function getHealthStatusLabel(status: HealthStatus): string {
  switch (status) {
    case 'green': return 'Healthy';
    case 'yellow': return 'Moderate';
    case 'red': return 'At Risk';
    default: return 'Unknown';
  }
}

export function getScoreRating(score: number): { label: string; color: string } {
  if (score >= 85) return { label: 'Exceptional', color: '#22c55e' };
  if (score >= 75) return { label: 'Strong', color: '#84cc16' };
  if (score >= 60) return { label: 'Solid', color: '#f59e0b' };
  if (score >= 40) return { label: 'Weak', color: '#f97316' };
  return { label: 'Fragile', color: '#ef4444' };
}

export function formatMetricValue(metric: Metric): string {
  const value = metric.current_value;
  if (value.numeric !== null) {
    if (value.unit === '%') return `${value.numeric}%`;
    if (value.unit === '$') return formatCurrency(value.numeric);
    if (value.unit === 'days') return `${value.numeric} days`;
    if (value.unit === 'months') return `${value.numeric} months`;
    return `${value.numeric}${value.unit || ''}`;
  }
  return value.text || 'N/A';
}

export function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}
