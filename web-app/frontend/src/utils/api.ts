import axios from 'axios';

let API_BASE_URL = '';

export const api = axios.create({
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthCheck = error.config?.url === '/api/auth/me';
    if (error.response?.status === 401 && !isAuthCheck) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export async function initializeApi(): Promise<void> {
  const response = await fetch('/api/runtime');
  const config = await response.json();
  API_BASE_URL = config.apiBaseUrl;
  api.defaults.baseURL = API_BASE_URL;
}

export function getLoginUrl(): string {
  return `${API_BASE_URL}/api/auth/login`;
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}
