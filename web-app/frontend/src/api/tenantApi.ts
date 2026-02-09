import { api } from '../utils/api';

export interface Tenant {
  id: string;
  azure_tenant_id: string | null;
  company_name: string;
  status: 'pending' | 'active' | 'suspended';
  is_platform_tenant: boolean;
  consent_timestamp: string | null;
  created_at: string;
  updated_at: string;
}

export interface TenantListResponse {
  tenants: Tenant[];
  total: number;
}

export interface OnboardingPackage {
  tenant_id: string;
  company_name: string;
  onboarding_url: string;
  onboarding_code: string;
  expires_at: string;
}

export interface OnboardingValidation {
  valid: boolean;
  tenant_id: string | null;
  company_name: string | null;
  error: string | null;
}

export const tenantApi = {
  list: async (): Promise<TenantListResponse> => {
    const response = await api.get<TenantListResponse>('/api/tenants');
    return response.data;
  },

  get: async (id: string): Promise<Tenant> => {
    const response = await api.get<Tenant>(`/api/tenants/${id}`);
    return response.data;
  },

  create: async (companyName: string): Promise<Tenant> => {
    const response = await api.post<Tenant>('/api/tenants', { company_name: companyName });
    return response.data;
  },

  update: async (id: string, data: Partial<Tenant>): Promise<Tenant> => {
    const response = await api.put<Tenant>(`/api/tenants/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/tenants/${id}`);
  },

  generateOnboarding: async (id: string): Promise<OnboardingPackage> => {
    const response = await api.post<OnboardingPackage>(`/api/tenants/${id}/onboarding`);
    return response.data;
  },

  validateOnboardingCode: async (code: string): Promise<OnboardingValidation> => {
    const response = await api.get<OnboardingValidation>(`/api/onboarding/validate/${code}`);
    return response.data;
  },
};
