import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

vi.mock('../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

import api from '../services/api';
import { mensagemErro, useCasoStore } from './caso';

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

describe('stores/caso', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('busca casos enviando só os filtros preenchidos e guarda o resultado', async () => {
    mockApi.get.mockResolvedValue({ data: { items: [{ id: 1, identificador_interno: 'HP-0001/26' }], total: 1 } });
    const store = useCasoStore();
    await store.buscar({ solicitacao: ' 123 ', prontuario: '', tipo_exame: 'HP' }, 2, 20);
    expect(mockApi.get).toHaveBeenCalledWith('/api/casos', { params: { pagina: 2, limite: 20, solicitacao: '123', tipo_exame: 'HP' } });
    expect(store.casos[0].identificador_interno).toBe('HP-0001/26');
    expect(store.total).toBe(1);
    expect(store.loading).toBe(false);
  });

  it('libera o loading mesmo quando a busca falha', async () => {
    mockApi.get.mockRejectedValue(new Error('rede'));
    const store = useCasoStore();
    await expect(store.buscar({}, 1, 20)).rejects.toThrow('rede');
    expect(store.loading).toBe(false);
  });

  it('chama as rotas de abertura e das ações do caso', async () => {
    mockApi.post.mockResolvedValue({ data: {} });
    const store = useCasoStore();
    await store.abrir('123', 'HP');
    await store.concluirEtapa(7);
    await store.encaminhar(7, 'IHQ', 'painel');
    await store.retornar(7, 'ajuste feito');
    expect(mockApi.post.mock.calls).toEqual([
      ['/api/casos', { solicitacao_aghu: '123', tipo_exame: 'HP' }],
      ['/api/casos/7/concluir-etapa'],
      ['/api/casos/7/encaminhar', { destino: 'IHQ', motivo: 'painel' }],
      ['/api/casos/7/retornar', { motivo: 'ajuste feito' }],
    ]);
  });

  it('extrai a mensagem de erro da API', () => {
    expect(mensagemErro({ response: { data: { detail: 'Caso não encontrado.' } } })).toBe('Caso não encontrado.');
    expect(mensagemErro({ response: { data: { detail: [{ msg: 'campo obrigatório' }] } } })).toBe('campo obrigatório');
    expect(mensagemErro(new Error('x'), 'padrão')).toBe('padrão');
  });
});
