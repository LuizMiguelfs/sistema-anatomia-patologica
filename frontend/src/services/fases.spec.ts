import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));

import api from './api';
import type { CampoFormulario } from './fases';
import { camposFaltando, concluirFormulario, dadosParaEnvio, listarFila, rotuloAmostra, salvarFormulario } from './fases';

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

describe('rotuloAmostra', () => {
  it('mostra o rótulo do SAP e a descrição, diferenciando amostras da mesma solicitação', () => {
    const a1 = { id: 1, amostra_aghu: '1', identificador: 'HP-0001/26-A1', descricao: 'Corpo gástrico' };
    const a2 = { id: 2, amostra_aghu: '2', identificador: 'HP-0001/26-A2', descricao: 'Corpo gástrico' };
    expect(rotuloAmostra(a1)).toBe('HP-0001/26-A1 — Corpo gástrico');
    expect(rotuloAmostra(a1)).not.toBe(rotuloAmostra(a2));
  });

  it('sem rótulo nem descrição, usa o número da amostra no AGHU', () => {
    expect(rotuloAmostra({ id: 3, amostra_aghu: 4, descricao: null })).toBe('Amostra 4');
    expect(rotuloAmostra({ id: 3, amostra_aghu: 4, descricao: '  ' , identificador: 'CG-0002/26-A4' })).toBe('CG-0002/26-A4');
  });
});
