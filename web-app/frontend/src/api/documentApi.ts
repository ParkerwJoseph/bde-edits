import { api } from '../utils/api';

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type DocumentType = 'pdf' | 'docx' | 'xlsx';
export type BDEPillar =
  | 'financial_health'
  | 'gtm_engine'
  | 'customer_health'
  | 'product_technical'
  | 'operational_maturity'
  | 'leadership_transition'
  | 'ecosystem_dependency'
  | 'service_software_ratio'
  | 'general';
export type ChunkType = 'text' | 'table' | 'chart' | 'image' | 'mixed';

export interface Document {
  id: string;
  tenant_id: string;
  company_id: string;
  uploaded_by: string;
  filename: string;
  original_filename: string;
  file_type: DocumentType;
  file_size: number;
  status: DocumentStatus;
  total_pages: number | null;
  processed_pages: number | null;
  error_message: string | null;
  chunk_count?: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  content: string;
  summary: string;
  previous_context: string | null;
  pillar: BDEPillar;
  chunk_type: ChunkType;
  page_number: number;
  chunk_index: number;
  confidence_score: number | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export interface DocumentWithChunks {
  document: Document;
  chunks: DocumentChunk[];
  chunk_count: number;
}

export interface ProcessingStatus {
  document_id: string;
  status: DocumentStatus;
  total_pages: number | null;
  processed_pages: number | null;
  error_message: string | null;
  chunk_count: number;
}

export interface CachedProgress {
  document_id: string;
  has_progress: boolean;
  status: string;
  step?: number;
  step_name?: string;
  progress?: number;
  error_message?: string;
}

export interface BatchProgressResponse {
  progress: Record<string, {
    status: string;
    total_pages: number | null;
    processed_pages: number | null;
    cached_progress?: {
      step: number;
      step_name: string;
      progress: number;
      status: string;
    };
  }>;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  message: string;
}

export interface DownloadUrlResponse {
  download_url: string;
  filename: string;
  content_type: string | null;
}

export const PILLAR_LABELS: Record<BDEPillar, string> = {
  financial_health: 'Financial Health',
  gtm_engine: 'GTM Engine & Predictability',
  customer_health: 'Customer Health & Expansion',
  product_technical: 'Product & Technical Maturity',
  operational_maturity: 'Operational Maturity',
  leadership_transition: 'Leadership & Transition Risk',
  ecosystem_dependency: 'Ecosystem Dependency',
  service_software_ratio: 'Service-to-Software Ratio',
  general: 'General',
};

export const PILLAR_COLORS: Record<BDEPillar, string> = {
  financial_health: '#22c55e',
  gtm_engine: '#3b82f6',
  customer_health: '#f59e0b',
  product_technical: '#8b5cf6',
  operational_maturity: '#ec4899',
  leadership_transition: '#f97316',
  ecosystem_dependency: '#06b6d4',
  service_software_ratio: '#84cc16',
  general: '#6b7280',
};

export const documentApi = {
  upload: async (file: File, companyId: string): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('company_id', companyId);

    const response = await api.post<UploadResponse>('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  list: async (params?: {
    status?: DocumentStatus;
    file_type?: DocumentType;
    company_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<DocumentListResponse> => {
    const response = await api.get<DocumentListResponse>('/api/documents/', { params });
    return response.data;
  },

  get: async (documentId: string): Promise<DocumentWithChunks> => {
    const response = await api.get<DocumentWithChunks>(`/api/documents/${documentId}`);
    return response.data;
  },

  getStatus: async (documentId: string): Promise<ProcessingStatus> => {
    const response = await api.get<ProcessingStatus>(`/api/documents/${documentId}/status`);
    return response.data;
  },

  // Get status for multiple documents in parallel (for polling fallback)
  getStatusBatch: async (documentIds: string[]): Promise<Map<string, ProcessingStatus>> => {
    const results = new Map<string, ProcessingStatus>();
    const promises = documentIds.map(async (id) => {
      try {
        const status = await api.get<ProcessingStatus>(`/api/documents/${id}/status`);
        results.set(id, status.data);
      } catch {
        // Ignore errors for individual documents
      }
    });
    await Promise.all(promises);
    return results;
  },

  // Get cached progress for a single document (includes step/progress info)
  getProgress: async (documentId: string): Promise<CachedProgress> => {
    const response = await api.get<CachedProgress>(`/api/documents/${documentId}/progress`);
    return response.data;
  },

  // Get cached progress for multiple documents (batch)
  getProgressBatch: async (documentIds: string[]): Promise<BatchProgressResponse> => {
    const response = await api.post<BatchProgressResponse>('/api/documents/progress/batch', documentIds);
    return response.data;
  },

  getChunks: async (
    documentId: string,
    params?: {
      pillar?: BDEPillar;
      chunk_type?: ChunkType;
      page_number?: number;
    }
  ): Promise<DocumentChunk[]> => {
    const response = await api.get<DocumentChunk[]>(`/api/documents/${documentId}/chunks`, {
      params,
    });
    return response.data;
  },

  delete: async (documentId: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/api/documents/${documentId}`);
    return response.data;
  },

  getDownloadUrl: async (documentId: string): Promise<DownloadUrlResponse> => {
    const response = await api.get<DownloadUrlResponse>(`/api/documents/${documentId}/download`);
    return response.data;
  },
};
