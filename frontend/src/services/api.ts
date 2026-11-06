import axios from 'axios';
import type { AxiosError } from 'axios';
import { getActivePinia } from 'pinia';
import type { InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../stores/auth';

const api = axios.create({
  baseURL: '/',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };
const authEndpoints = ['/api/login', '/api/token/refresh', '/api/logout'];
const isAuthEndpoint = (url?: string) => authEndpoints.some(path => (url || '').split('?')[0].endsWith(path));

api.interceptors.request.use(config => {
  // fetchSystemConfig() é chamado durante import dos módulos, antes de app.use(pinia).
  const token = getActivePinia() ? useAuthStore().accessToken : null;
  if (token && !isAuthEndpoint(config.url)) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined;
    if (!original || error.response?.status !== 401 || original._retry || isAuthEndpoint(original.url) || !getActivePinia()) {
      return Promise.reject(error);
    }

    original._retry = true;
    if (!refreshPromise) {
      // Cliente Axios separado impede recursão infinita nos interceptadores.
      refreshPromise = axios.post<{ access_token: string }>('/api/token/refresh', undefined, {
        withCredentials: true,
      }).then(response => {
        useAuthStore().setToken(response.data.access_token);
        return response.data.access_token;
      }).finally(() => { refreshPromise = null; });
    }
    try {
      const token = await refreshPromise;
      original.headers.Authorization = `Bearer ${token}`;
      return api(original);
    } catch (refreshError) {
      useAuthStore().clearToken();
      // Evita dependência circular estática entre api.ts e router/index.ts.
      const router = (await import('../router')).default;
      if (router.currentRoute.value.name !== 'Login') {
        await router.replace({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } });
      }
      return Promise.reject(refreshError);
    }
  },
);

export default api;
