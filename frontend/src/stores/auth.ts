import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { Router } from 'vue-router';
import api from '../services/api';

export type SapRole = 'RECEPCAO' | 'LABORATORIO' | 'RESIDENTE' | 'PRECEPTORIA' | 'CHEFIA';
export interface User {
  username: string;
  role: SapRole;
  groups: string[];
  displayName?: string[];
  email?: string[];
  department?: string[];
  title?: string[];
  givenName?: string[];
  userPrincipalName?: string[];
  employeeNumber?: string[];
}

export const useAuthStore = defineStore('auth', () => {
  // Evita guardar credenciais em localStorage/sessionStorage.
  const accessToken = ref<string | null>(null);
  const user = ref<User | null>(null);
  const initialized = ref(false);
  let initializing: Promise<void> | null = null;

  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value));
  const role = computed(() => user.value?.role ?? null);
  const isAdmin = computed(() => user.value?.groups.includes('GLO-SEC-HCPE-SETISD') ?? false);
  const isChefia = computed(() => role.value === 'CHEFIA');
  const hasRole = (...roles: SapRole[]) => user.value !== null && roles.includes(user.value.role);

  const setToken = (value: string) => { accessToken.value = value; };
  const setUser = (value: User | null) => { user.value = value; };
  const clearToken = () => {
    accessToken.value = null;
    user.value = null;
    // Limpeza defensiva de tokens legados da versão anterior.
    localStorage.removeItem('accessToken');
  };

  async function fetchUser() {
    if (!accessToken.value) {
      setUser(null);
      return;
    }
    const { data } = await api.get<User>('/api/users/me');
    setUser(data);
  }

  async function login(username: string, password: string, rememberMe: boolean) {
    clearToken();
    const params = new URLSearchParams();
    params.set('username', username.trim());
    params.set('password', password);
    params.set('remember_me', String(rememberMe));
    const { data } = await api.post<{ access_token: string }>('/api/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    setToken(data.access_token);
    try {
      await fetchUser();
    } catch (error) {
      clearToken();
      throw error;
    }
    initialized.value = true;
  }

  async function initializeAuth() {
    if (initialized.value) return;
    if (initializing) return initializing;
    initializing = (async () => {
      try {
        // A restauração funciona tanto depois de reload quanto quando access token expirou.
        const { data } = await api.post<{ access_token: string }>('/api/token/refresh');
        setToken(data.access_token);
        await fetchUser();
      } catch (_error) {
        clearToken();
      } finally {
        initialized.value = true;
      }
    })();
    try { await initializing; } finally { initializing = null; }
  }

  async function logout(router?: Router) {
    try {
      await api.post('/api/logout');
    } finally {
      clearToken();
      initialized.value = true;
      if (router) await router.replace({ name: 'Login' });
    }
  }

  return {
    accessToken, user, initialized, isAuthenticated, role, isAdmin, isChefia,
    hasRole, setToken, setUser, clearToken, fetchUser, login, logout, initializeAuth,
  };
});
