import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

import api from './api';
import {
  TIPOS_EXAME, desfazerRetirada, listarSolicitacoes, marcarRetirado, mensagemErro, paramsDaBusca, rotuloEtapa,
} from './solicitacoes';

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

describe('services/solicitacoes', () => {
  beforeEach(() => vi.clearAllMocks());

  it('não envia filtros vazios e apara espaços', () => {
    expect(paramsDaBusca('NAO_RETIRADO', { tipo_exame: '', busca: ' 123 ', de: '2026-11-01' }, 2, 20)).toEqual({
      situacao: 'NAO_RETIRADO', pagina: 2, limite: 20, busca: '123', de: '2026-11-01',
    });
  });

  it('lista com a situação pedida', async () => {
    mockApi.get.mockResolvedValue({ data: { items: [], total: 0, pagina: 1, limite: 20 } });
    await listarSolicitacoes('RETIRADO', { tipo_exame: 'HP' });
    expect(mockApi.get).toHaveBeenCalledWith('/api/solicitacoes', {
      params: { situacao: 'RETIRADO', pagina: 1, limite: 20, tipo_exame: 'HP' },
    });
  });

  it('marca e desfaz a retirada', async () => {
    mockApi.post.mockResolvedValue({ data: {} });
    await marcarRetirado(7);
    await desfazerRetirada(7);
    expect(mockApi.post).toHaveBeenNthCalledWith(1, '/api/solicitacoes/7/retirar');
    expect(mockApi.post).toHaveBeenNthCalledWith(2, '/api/solicitacoes/7/desfazer-retirada');
  });

  it('tem os seis tipos de exame e rótulos de etapa', () => {
    expect(TIPOS_EXAME.map((t) => t.valor)).toEqual(['HP', 'CO', 'CG', 'CCV', 'IHQ', 'RL']);
    expect(rotuloEtapa('PROCESSAMENTO')).toBe('Processamento Técnico');
    expect(rotuloEtapa('X')).toBe('X');
  });

  it('extrai a mensagem de erro da API', () => {
    expect(mensagemErro({ response: { data: { detail: 'Sem permissão' } } })).toBe('Sem permissão');
    expect(mensagemErro({}, 'padrão')).toBe('padrão');
  });
});
