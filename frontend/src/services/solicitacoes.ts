/**
 * Serviço de Solicitações de Exames (MVP): listas "Não retirados" e "Retirados".
 *
 * Fala com /api/solicitacoes. Só a Recepção marca (ou desfaz) a retirada; o backend confere.
 */
import api from './api';

export type SituacaoRetirada = 'NAO_RETIRADO' | 'RETIRADO';

/** Linha das listas de solicitações. */
export interface SolicitacaoExame {
  id: number;
  identificador_interno: string;
  solicitacao_aghu: string | number;
  paciente_nome: string;
  prontuario_aghu: string | number | null;
  tipo_exame: string;
  etapa_atual: string;
  status: string;
  urgente: boolean;
  criado_em: string;
  retirado_em: string | null;
  retirado_por: string | null;
  qtd_amostras: number;
  descricao_amostras: string | null;
}

export interface PaginaSolicitacoes {
  items: SolicitacaoExame[];
  total: number;
  pagina: number;
  limite: number;
}

/** Filtros das duas abas: tipo de exame, período e busca pelos três códigos do dia a dia. */
export interface FiltrosSolicitacoes {
  tipo_exame?: string;
  de?: string;
  ate?: string;
  busca?: string;
}

/** Tipos de exame com o rótulo usado nas telas. */
export const TIPOS_EXAME: ReadonlyArray<{ valor: string; rotulo: string }> = [
  { valor: 'HP', rotulo: 'Histopatológico (HP)' },
  { valor: 'CO', rotulo: 'Congelação (CO)' },
  { valor: 'CG', rotulo: 'Citologia Geral (CG)' },
  { valor: 'CCV', rotulo: 'Cérvico-vaginal (CCV)' },
  { valor: 'IHQ', rotulo: 'Imunohistoquímico (IHQ)' },
  { valor: 'RL', rotulo: 'Revisão de Lâmina (RL)' },
];

/** Rótulos das etapas do fluxo. */
export const ETAPAS: Readonly<Record<string, string>> = {
  RECEPCAO: 'Recepção',
  MACROSCOPIA: 'Macroscopia',
  CONGELACAO: 'Congelação',
  PROCESSAMENTO: 'Processamento Técnico',
  IHQ: 'IHQ',
  MICROSCOPIA: 'Microscopia',
  REVISAO: 'Revisão de Lâmina',
  REDE_EXTERNA: 'Rede externa',
  ARQUIVO: 'Arquivada',
};

/** Rótulo legível de uma etapa; devolve o próprio valor se for desconhecida. */
export function rotuloEtapa(etapa: string): string {
  return ETAPAS[etapa] ?? etapa;
}

/** Monta os parâmetros da consulta, sem enviar filtros vazios. */
export function paramsDaBusca(
  situacao: SituacaoRetirada, filtros: FiltrosSolicitacoes, pagina: number, limite: number,
): Record<string, string | number> {
  const params: Record<string, string | number> = { situacao, pagina, limite };
  Object.entries(filtros).forEach(([chave, valor]) => {
    if (valor && String(valor).trim()) params[chave] = String(valor).trim();
  });
  return params;
}

/** Lista "Não retirados" (urgentes no topo, mais antigo primeiro) ou "Retirados" (mais recente primeiro). */
export async function listarSolicitacoes(
  situacao: SituacaoRetirada, filtros: FiltrosSolicitacoes, pagina = 1, limite = 20,
): Promise<PaginaSolicitacoes> {
  const { data } = await api.get<PaginaSolicitacoes>('/api/solicitacoes', {
    params: paramsDaBusca(situacao, filtros, pagina, limite),
  });
  return data;
}

/** Recepção marca o material como retirado (a solicitação segue para a próxima fase). */
export async function marcarRetirado(id: number): Promise<void> {
  await api.post(`/api/solicitacoes/${id}/retirar`);
}

/** Recepção desfaz a retirada (a solicitação volta para "Não retirados"). */
export async function desfazerRetirada(id: number): Promise<void> {
  await api.post(`/api/solicitacoes/${id}/desfazer-retirada`);
}

/** Extrai a mensagem padrão {"detail": "..."} devolvida pela API. */
export function mensagemErro(error: unknown, padrao = 'Não foi possível concluir a operação.'): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return padrao;
}

/** Data e hora no fuso do hospital (America/Recife). */
export function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR', {
    timeZone: 'America/Recife', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}
