import { api, getApiBaseUrl } from '../utils/api';

// Get WebSocket URL from API base URL
function getWsUrl(): string {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    // Fallback to current host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}`;
  }
  // Convert http(s) to ws(s)
  return baseUrl.replace(/^http/, 'ws');
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface SourceInfo {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  pillar: string;
  pillar_label: string;
  similarity: number;
  summary: string;
  // Connector-specific fields
  source_type?: 'document' | 'connector';
  connector_type?: string;  // e.g., "quickbooks"
  entity_type?: string;     // e.g., "invoice", "customer"
  entity_name?: string;     // Human-readable entity name
}

export interface ChunkInfo {
  id: string;
  document_id: string;
  content: string;
  summary: string | null;
  previous_context: string | null;
  pillar: string;
  chunk_type: string;
  page_number: number;
  similarity: number;
}

export interface ChatRequest {
  query: string;
  session_id?: string | null;
  company_id?: string | null;
  document_ids?: string[] | null;
  conversation_history?: ChatMessage[];
  top_k?: number;
}

export interface ChatResponse {
  answer: string;
  sources: SourceInfo[];
  chunks: ChunkInfo[];
  usage_stats: Record<string, number>;
  session_id?: string;
}

export interface SearchRequest {
  query: string;
  document_ids?: string[] | null;
  top_k?: number;
  similarity_threshold?: number;
}

export interface SearchResponse {
  chunks: ChunkInfo[];
  total: number;
}

// Chat Session Types

export interface ChatSession {
  id: string;
  title: string;
  company_id?: string | null;
  document_ids?: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageResponse {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceInfo[] | null;
  usage_stats?: Record<string, number> | null;
  created_at: string;
}

export interface ChatSessionDetail {
  id: string;
  title: string;
  company_id?: string | null;
  document_ids?: string[] | null;
  messages: ChatMessageResponse[];
  created_at: string;
  updated_at: string;
}

export interface ChatSessionListResponse {
  sessions: ChatSession[];
  total: number;
}

export interface ChatSessionCreateRequest {
  title?: string;
  company_id?: string | null;
  document_ids?: string[] | null;
}

export interface ChatSessionUpdateRequest {
  title?: string;
  document_ids?: string[] | null;
}

// WebSocket Stream Callbacks
export interface StreamCallbacks {
  onConnected?: () => void;
  onStatus?: (phase: string, message: string) => void;
  onSession?: (sessionId: string) => void;
  onSources?: (sources: SourceInfo[], chunks: ChunkInfo[]) => void;
  onChunk?: (chunk: string, fullText: string) => void;
  onDone?: (fullText: string) => void;
  onError?: (error: string) => void;
}

// WebSocket connection manager for chat
class ChatWebSocket {
  private ws: WebSocket | null = null;
  private isConnected = false;

  async connect(): Promise<void> {
    if (this.ws && this.isConnected) {
      return;
    }

    return new Promise((resolve, reject) => {
      const wsUrl = getWsUrl();
      console.log('[ChatWS] Connecting to:', `${wsUrl}/api/chat/ws`);
      this.ws = new WebSocket(`${wsUrl}/api/chat/ws`);

      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'));
      }, 10000);

      this.ws.onopen = () => {
        console.log('[ChatWS] Connected, sending auth...');
        this.ws?.send(JSON.stringify({ type: 'auth' }));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[ChatWS] Received:', data.type);

          if (data.type === 'connected') {
            clearTimeout(timeout);
            this.isConnected = true;
            resolve();
          } else if (data.type === 'error' && !this.isConnected) {
            clearTimeout(timeout);
            reject(new Error(data.message || 'Connection failed'));
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onerror = () => {
        console.error('[ChatWS] Connection error');
        clearTimeout(timeout);
        reject(new Error('WebSocket connection error'));
      };

      this.ws.onclose = () => {
        console.log('[ChatWS] Connection closed');
        this.isConnected = false;
        this.ws = null;
      };
    });
  }

  async sendQuery(request: ChatRequest, callbacks: StreamCallbacks): Promise<void> {
    if (!this.ws || !this.isConnected) {
      await this.connect();
    }

    return new Promise((resolve, reject) => {
      if (!this.ws) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      let fullText = '';

      const messageHandler = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'status':
              callbacks.onStatus?.(data.phase, data.message);
              break;
            case 'session':
              callbacks.onSession?.(data.session_id);
              break;
            case 'sources':
              callbacks.onSources?.(data.data.sources, data.data.chunks);
              break;
            case 'chunk':
              fullText += data.data;
              callbacks.onChunk?.(data.data, fullText);
              break;
            case 'done':
              callbacks.onDone?.(fullText);
              this.ws?.removeEventListener('message', messageHandler);
              resolve();
              break;
            case 'error':
              callbacks.onError?.(data.message);
              this.ws?.removeEventListener('message', messageHandler);
              reject(new Error(data.message));
              break;
            case 'ping':
              this.ws?.send(JSON.stringify({ type: 'pong' }));
              break;
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.addEventListener('message', messageHandler);

      // Send the query
      this.ws.send(JSON.stringify({
        type: 'query',
        data: {
          query: request.query,
          session_id: request.session_id,
          company_id: request.company_id,
          document_ids: request.document_ids,
          top_k: request.top_k || 5,
        },
      }));
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }
}

// Singleton WebSocket instance
const chatWs = new ChatWebSocket();

export const chatApi = {
  // Chat endpoints
  chat: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/api/chat/chat', request);
    return response.data;
  },

  // Streaming chat via WebSocket
  chatStream: async (request: ChatRequest, callbacks: StreamCallbacks): Promise<void> => {
    return chatWs.sendQuery(request, callbacks);
  },

  search: async (request: SearchRequest): Promise<SearchResponse> => {
    const response = await api.post<SearchResponse>('/api/chat/search', request);
    return response.data;
  },

  // Session endpoints
  listSessions: async (companyId?: string, skip: number = 0, limit: number = 50): Promise<ChatSessionListResponse> => {
    const response = await api.get<ChatSessionListResponse>('/api/chat/sessions', {
      params: { company_id: companyId, skip, limit }
    });
    return response.data;
  },

  createSession: async (request: ChatSessionCreateRequest): Promise<ChatSession> => {
    const response = await api.post<ChatSession>('/api/chat/sessions', request);
    return response.data;
  },

  getSession: async (sessionId: string): Promise<ChatSessionDetail> => {
    const response = await api.get<ChatSessionDetail>(`/api/chat/sessions/${sessionId}`);
    return response.data;
  },

  updateSession: async (sessionId: string, request: ChatSessionUpdateRequest): Promise<ChatSession> => {
    const response = await api.patch<ChatSession>(`/api/chat/sessions/${sessionId}`, request);
    return response.data;
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/api/chat/sessions/${sessionId}`);
  },
};
