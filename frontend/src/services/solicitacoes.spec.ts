import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

import api from './api';
import type { PreviaAghu } from './solicitacoes';
import {
  TIPOS_EXAME, abrirSolicitacao, consultarSolicitacaoAghu, desfazerRetirada, formatarData, listarSolicitacoes,
  marcarRetirado, mensagemErro, paramsDaBusca, podeAbrir, rotuloEtapa, textoPendencia,
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

describe('abertura de solicitação a partir do AGHU', () => {
  beforeEach(() => vi.clearAllMocks());

  const previa = (extra: Partial<PreviaAghu> = {}): PreviaAghu => ({
    solicitacao_aghu: 800002, paciente_nome: 'A.F.', prontuario_aghu: '90000001', tipo_exame: 'HP', tipos_exame: ['HP'],
    pendencias: [], urgente: false, data_solicitacao: '2026-03-11', origem: 'Ambulatório', unidade: null,
    especialidade: null, convenio: 'SUS', status_aghu: 'LI', status_descricao: 'LIBERADO', qtd_amostras: 1,
    amostras_canceladas: 0, amostras: [{ amostra_aghu: 1, id_amostra: '800002-1' }], solicitacao_existente: null,
    ...extra,
  });

  it('consulta a prévia e abre enviando só o número', async () => {
    mockApi.get.mockResolvedValue({ data: previa() });
    mockApi.post.mockResolvedValue({ data: { id: 1 } });
    await consultarSolicitacaoAghu(' 800002 ');
    await abrirSolicitacao(' 800002 ');
    expect(mockApi.get).toHaveBeenCalledWith('/api/solicitacoes/aghu/solicitacao/800002');
    expect(mockApi.post).toHaveBeenCalledWith('/api/solicitacoes', { solicitacao_aghu: '800002' });
  });

  it('só permite abrir sem pendência, com tipo, com amostra e ainda não aberta', () => {
    expect(podeAbrir(previa())).toBe(true);
    expect(podeAbrir(null)).toBe(false);
    expect(podeAbrir(previa({ tipo_exame: null, tipos_exame: ['CO', 'HP'], pendencias: ['TIPOS_CONFLITANTES'] }))).toBe(false);
    expect(podeAbrir(previa({ amostras: [] }))).toBe(false);
    expect(podeAbrir(previa({ solicitacao_existente: 'HP-0001/26' }))).toBe(false);
  });

  it('traduz pendências e formata a data do AGHU', () => {
    expect(textoPendencia('TIPOS_CONFLITANTES')).toContain('tipos de exame diferentes');
    expect(textoPendencia('OUTRA')).toBe('OUTRA');
    expect(formatarData('2026-03-11')).toBe('11/03/2026');
    expect(formatarData(null)).toBe('—');
  });
});
