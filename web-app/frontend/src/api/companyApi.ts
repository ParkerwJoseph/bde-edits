import { api } from '../utils/api';

export interface Company {
  id: string;
  tenant_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface CompanyListResponse {
  companies: Company[];
  total: number;
}

export interface CompanyCreateRequest {
  name: string;
}

export interface CompanyUpdateRequest {
  name?: string;
}

export const companyApi = {
  list: async (): Promise<CompanyListResponse> => {
    const response = await api.get<CompanyListResponse>('/api/companies');
    return response.data;
  },

  get: async (companyId: string): Promise<Company> => {
    const response = await api.get<Company>(`/api/companies/${companyId}`);
    return response.data;
  },

  create: async (data: CompanyCreateRequest): Promise<Company> => {
    const response = await api.post<Company>('/api/companies', data);
    return response.data;
  },

  update: async (companyId: string, data: CompanyUpdateRequest): Promise<Company> => {
    const response = await api.patch<Company>(`/api/companies/${companyId}`, data);
    return response.data;
  },

  delete: async (companyId: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/api/companies/${companyId}`);
    return response.data;
  },
};
