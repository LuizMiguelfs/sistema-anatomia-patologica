/**
 * Linha do tempo de uma solicitação de exame, montada a partir da trilha de auditoria
 * (GET /api/auditoria/historico). Aberta a todos os perfis ("vê tudo"): a API não devolve IP.
 */
import api from './api';
import { rotuloAcao } from './auditoria';
import { rotuloEtapa } from './solicitacoes';

/** Prefixo do recurso na trilha. Registros anteriores à T4.1 usam "caso:<id>"; a API devolve os dois. */
export const RECURSO_SOLICITACAO = 'solicitacao';

/** Limite da API por consulta; uma solicitação tem bem menos eventos que isso. */
export const LIMITE_HISTORICO = 200;

/** Evento como vem da API. */
export interface EventoHistorico {
  id: number;
  created_at: string;
  usuario: string;
  categoria: string;
  acao: string;
  recurso: string;
  dados_anteriores: unknown;
  dados_novos: unknown;
}

export interface PaginaHistorico {
  total: number;
  limite: number;
  offset: number;
  itens: EventoHistorico[];
}

/** Item pronto para a tela. */
export interface ItemLinhaDoTempo {
  id: number;
  quando: string;
  usuario: string;
  titulo: string;
  detalhe: string | null;
}

/** Encaminhar e retornar, com os códigos novos e os anteriores à T4.1. */
const ACOES_DE_MOVIMENTO = new Set(['ENCAMINHAR_SOLICITACAO', 'RETORNAR_SOLICITACAO', 'ENCAMINHAR_CASO', 'RETORNAR_CASO']);

/** Lê um campo de um objeto de dados da trilha (ou null). */
function campo(dados: unknown, nome: string): string | null {
  if (typeof dados !== 'object' || dados === null || Array.isArray(dados)) return null;
  const valor = (dados as Record<string, unknown>)[nome];
  return valor === null || valor === undefined || valor === '' ? null : String(valor);
}

/** Complemento curto do evento: para onde a solicitação seguiu, de onde voltou etc. */
export function detalheDoEvento(evento: EventoHistorico): string | null {
  const acao = evento.acao.toUpperCase();
  const destino = campo(evento.dados_novos, 'etapa_atual');
  if (acao === 'ABRIR_SOLICITACAO' || acao === 'ABRIR_CASO') {
    const codigo = campo(evento.dados_novos, 'identificador_interno');
    return codigo ? `Código interno ${codigo}` : null;
  }
  if (acao === 'DESFAZER_RETIRADA') {
    const origem = campo(evento.dados_anteriores, 'etapa_atual');
    return origem ? `Voltou de ${rotuloEtapa(origem)} para a Recepção` : 'Voltou para a Recepção';
  }
  if (acao === 'MARCAR_RETIRADO' || acao.startsWith('CONCLUIR_') || ACOES_DE_MOVIMENTO.has(acao)) {
    return destino ? `Seguiu para ${rotuloEtapa(destino)}` : null;
  }
  return null;
}

/** Eventos em ordem cronológica (do primeiro ao último), já com rótulos em português. */
export function montarLinhaDoTempo(eventos: EventoHistorico[]): ItemLinhaDoTempo[] {
  return [...eventos]
    .sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at) || a.id - b.id)
    .map((e) => ({
      id: e.id,
      quando: e.created_at,
      usuario: e.usuario,
      titulo: rotuloAcao(e.acao),
      detalhe: detalheDoEvento(e),
    }));
}

/** Busca o histórico da solicitação na trilha de auditoria. */
export async function listarHistorico(solicitacaoId: number): Promise<PaginaHistorico> {
  const { data } = await api.get<PaginaHistorico>('/api/auditoria/historico', {
    params: { recurso: `${RECURSO_SOLICITACAO}:${solicitacaoId}`, limite: LIMITE_HISTORICO },
  });
  return data;
}
