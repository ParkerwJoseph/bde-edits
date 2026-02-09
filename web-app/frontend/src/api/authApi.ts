import { api, getLoginUrl } from '../utils/api';

export interface TenantInfo {
  id: string;
  company_name: string;
  is_platform_tenant: boolean;
}

export interface RoleInfo {
  id: string;
  name: string;
  level: string;
}

export interface User {
  id: string;
  azure_oid: string;
  azure_tid: string;
  email: string | null;
  display_name: string | null;
  is_active: boolean;
  first_login_at: string | null;
  last_login_at: string | null;
  created_at: string | null;
  tenant: TenantInfo | null;
  role: RoleInfo | null;
  permissions: string[];
}

export const authApi = {
  login: (): void => {
    window.location.href = getLoginUrl();
  },

  logout: async (): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/api/auth/logout');
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await api.get<User>('/api/auth/me');
    return response.data;
  },
};
