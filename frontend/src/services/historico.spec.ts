import { beforeEach, describe, expect, it, vi } from 'vitest';

const get = vi.fn();
vi.mock('./api', () => ({ default: { get: (...args: unknown[]) => get(...args) } }));

import { detalheDoEvento, listarHistorico, montarLinhaDoTempo, type EventoHistorico } from './historico';

function evento(id: number, created_at: string, acao: string, extra: Partial<EventoHistorico> = {}): EventoHistorico {
  return {
    id, created_at, acao, usuario: 'demo.residente', categoria: 'NEGOCIO_CLINICO', recurso: 'caso:7',
    dados_anteriores: null, dados_novos: null, ...extra,
  };
}

describe('services/historico · linha do tempo', () => {
  beforeEach(() => get.mockReset());

  it('consulta a trilha pelo recurso da solicitação', async () => {
    get.mockResolvedValue({ data: { total: 0, limite: 200, offset: 0, itens: [] } });
    await listarHistorico(7);
    expect(get).toHaveBeenCalledWith('/api/auditoria/historico', { params: { recurso: 'caso:7', limite: 200 } });
  });

  it('põe os eventos em ordem: entrada, retirada, rascunho, conclusão', () => {
    // A API devolve os mais recentes primeiro.
    const itens = montarLinhaDoTempo([
      evento(4, '2026-11-17T15:00:00Z', 'CONCLUIR_MACROSCOPIA', { dados_novos: { etapa_atual: 'PROCESSAMENTO' } }),
      evento(3, '2026-11-17T14:00:00Z', 'SALVAR_MACROSCOPIA'),
      evento(2, '2026-11-17T13:00:00Z', 'MARCAR_RETIRADO', { usuario: 'demo.recepcao', dados_novos: { etapa_atual: 'MACROSCOPIA' } }),
      evento(1, '2026-11-17T12:00:00Z', 'ABRIR_CASO', { dados_novos: { identificador_interno: 'HP-0007/26' } }),
    ]);
    expect(itens.map((i) => i.titulo)).toEqual([
      'Entrada da solicitação no SAP',
      'Marcada como retirada',
      'Macroscopia: rascunho salvo',
      'Macroscopia: fase concluída',
    ]);
    expect(itens.map((i) => i.detalhe)).toEqual([
      'Código interno HP-0007/26', 'Seguiu para Macroscopia', null, 'Seguiu para Processamento Técnico',
    ]);
    expect(itens[1].usuario).toBe('demo.recepcao');
  });

  it('mesmo horário: desempata pela ordem de gravação', () => {
    const itens = montarLinhaDoTempo([
      evento(9, '2026-11-17T12:00:00Z', 'CONCLUIR_PROCESSAMENTO'),
      evento(8, '2026-11-17T12:00:00Z', 'SALVAR_PROCESSAMENTO'),
    ]);
    expect(itens.map((i) => i.id)).toEqual([8, 9]);
  });

  it('desfazer retirada diz de onde voltou', () => {
    expect(detalheDoEvento(evento(1, '2026-11-17T12:00:00Z', 'DESFAZER_RETIRADA', {
      dados_anteriores: { etapa_atual: 'CONGELACAO' }, dados_novos: { etapa_atual: 'RECEPCAO' },
    }))).toBe('Voltou de Congelação para a Recepção');
  });

  it('não expõe o conteúdo do formulário no detalhe', () => {
    const item = montarLinhaDoTempo([
      evento(1, '2026-11-17T12:00:00Z', 'SALVAR_MICROSCOPIA', { dados_novos: { diagnostico: 'texto clínico' } }),
    ])[0];
    expect(item.detalhe).toBeNull();
    expect(JSON.stringify(item)).not.toContain('texto clínico');
  });
});
