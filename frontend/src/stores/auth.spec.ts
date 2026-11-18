import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

vi.mock('../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

import { useAuthStore, type SapRole, type User } from './auth';
import { PERFIS_SAP } from '../services/usuarios';

function usuario(role: SapRole, extra: Partial<User> = {}): User {
  return { username: 'caio.res', role, groups: [], ...extra };
}

describe('stores/auth · perfil logado', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('sem usuário, não há perfil nem nome para mostrar', () => {
    const store = useAuthStore();
    expect(store.perfilRotulo).toBeNull();
    expect(store.perfilRotuloCurto).toBeNull();
    expect(store.nomeExibicao).toBeNull();
  });

  it('mostra o perfil com o mesmo rótulo usado em Configurações', () => {
    const store = useAuthStore();
    for (const perfil of PERFIS_SAP) {
      store.setUser(usuario(perfil.valor));
      expect(store.perfilRotulo).toBe(perfil.rotulo);
    }
  });

  it('exemplo do plano: quem entra como RESIDENTE vê "Residentes"', () => {
    const store = useAuthStore();
    store.setUser(usuario('RESIDENTE'));
    expect(store.perfilRotulo).toBe('Residentes');
  });

  it('tem versão curta para o celular', () => {
    const store = useAuthStore();
    store.setUser(usuario('CHEFIA'));
    expect(store.perfilRotulo).toBe('Técnico Administrativo (Chefia do UACAP)');
    expect(store.perfilRotuloCurto).toBe('Chefia');
    store.setUser(usuario('PRECEPTORIA'));
    expect(store.perfilRotuloCurto).toBe('Preceptoria');
  });

  it('usa o nome do AD quando existe e o login quando não', () => {
    const store = useAuthStore();
    store.setUser(usuario('RESIDENTE', { displayName: ['Caio Residente'] }));
    expect(store.nomeExibicao).toBe('Caio Residente');
    store.setUser(usuario('RESIDENTE', { displayName: ['  '] }));
    expect(store.nomeExibicao).toBe('caio.res');
  });

  it('ao sair, perfil e nome somem', () => {
    vi.stubGlobal('localStorage', { removeItem: vi.fn() }); // ambiente de teste sem navegador
    const store = useAuthStore();
    store.setUser(usuario('CHEFIA'));
    store.clearToken();
    expect(store.perfilRotulo).toBeNull();
    expect(store.nomeExibicao).toBeNull();
    vi.unstubAllGlobals();
  });
});
