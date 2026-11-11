import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));

import api from './api';
import type { CampoFormulario } from './fases';
import { camposFaltando, concluirFormulario, dadosParaEnvio, listarFila, salvarFormulario } from './fases';

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn>; put: ReturnType<typeof vi.fn>;
};

const CAMPOS: CampoFormulario[] = [
  { nome: 'descricao', rotulo: 'Descrição', tipo: 'texto_longo', obrigatorio: true, editavel: true },
  { nome: 'qtd', rotulo: 'Quantidade', tipo: 'numero', obrigatorio: true, editavel: true },
  { nome: 'diagnostico', rotulo: 'Diagnóstico', tipo: 'texto_longo', obrigatorio: true, editavel: false },
  { nome: 'obs', rotulo: 'Observações', tipo: 'texto_longo', obrigatorio: false, editavel: true },
];

describe('services/fases', () => {
  beforeEach(() => vi.clearAllMocks());

  it('aponta os obrigatórios vazios', () => {
    expect(camposFaltando(CAMPOS, { descricao: '  ', qtd: 0 })).toEqual(['Descrição', 'Diagnóstico']);
  });

  it('envia só o que o perfil edita, com números como número', () => {
    expect(dadosParaEnvio(CAMPOS, { descricao: 'x', qtd: '3', diagnostico: 'não enviar', obs: '' })).toEqual({
      descricao: 'x', qtd: 3, obs: null,
    });
  });

  it('busca a fila da fase sem filtros vazios', async () => {
    mockApi.get.mockResolvedValue({ data: { items: [] } });
    await listarFila('MACROSCOPIA', { tipo_exame: '', busca: 'HP-0001/26' });
    expect(mockApi.get).toHaveBeenCalledWith('/api/fases/MACROSCOPIA/fila', {
      params: { pagina: 1, limite: 50, busca: 'HP-0001/26' },
    });
  });

  it('salva com PUT e conclui com POST', async () => {
    mockApi.put.mockResolvedValue({ data: {} });
    mockApi.post.mockResolvedValue({ data: {} });
    await salvarFormulario('MICROSCOPIA', 3, { pre_laudo: 'a' });
    await concluirFormulario('MICROSCOPIA', 3, { diagnostico: 'b' });
    expect(mockApi.put).toHaveBeenCalledWith('/api/fases/MICROSCOPIA/solicitacoes/3', { dados: { pre_laudo: 'a' } });
    expect(mockApi.post).toHaveBeenCalledWith('/api/fases/MICROSCOPIA/solicitacoes/3/concluir', { dados: { diagnostico: 'b' } });
  });
});
