import { api } from '../utils/api';

export interface UserWithDetails {
  id: string;
  email: string | null;
  display_name: string | null;
  is_active: boolean;
  first_login_at: string | null;
  last_login_at: string | null;
  created_at: string;
  tenant_name: string | null;
  role_name: string | null;
}

export interface UserListResponse {
  users: UserWithDetails[];
  total: number;
}

export const userApi = {
  list: async (tenantId?: string): Promise<UserListResponse> => {
    const params = tenantId ? { tenant_id: tenantId } : {};
    const response = await api.get<UserListResponse>('/api/users', { params });
    return response.data;
  },

  get: async (id: string): Promise<UserWithDetails> => {
    const response = await api.get<UserWithDetails>(`/api/users/${id}`);
    return response.data;
  },

  updateRole: async (id: string, roleName: string): Promise<UserWithDetails> => {
    const response = await api.put<UserWithDetails>(`/api/users/${id}/role`, { role_name: roleName });
    return response.data;
  },

  updateStatus: async (id: string, isActive: boolean): Promise<UserWithDetails> => {
    const response = await api.put<UserWithDetails>(`/api/users/${id}/status`, { is_active: isActive });
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/users/${id}`);
  },
};
