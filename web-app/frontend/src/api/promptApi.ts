import { api } from '../utils/api';

export interface PromptTemplate {
  id: string;
  name: string;
  description: string | null;
  template: string;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  updated_by: string | null;
}

export interface PromptUpdate {
  template: string;
}

export interface DefaultPromptResponse {
  template: string;
}

export const promptApi = {
  /**
   * Get the active RAG prompt template.
   */
  get: async (): Promise<PromptTemplate> => {
    const response = await api.get<PromptTemplate>('/api/prompts');
    return response.data;
  },

  /**
   * Update the RAG prompt template.
   */
  update: async (data: PromptUpdate): Promise<PromptTemplate> => {
    const response = await api.put<PromptTemplate>('/api/prompts', data);
    return response.data;
  },

  /**
   * Reset the prompt to default.
   */
  reset: async (): Promise<PromptTemplate> => {
    const response = await api.post<PromptTemplate>('/api/prompts/reset');
    return response.data;
  },

  /**
   * Get the default prompt template (for reference).
   */
  getDefault: async (): Promise<DefaultPromptResponse> => {
    const response = await api.get<DefaultPromptResponse>('/api/prompts/default');
    return response.data;
  },
};
