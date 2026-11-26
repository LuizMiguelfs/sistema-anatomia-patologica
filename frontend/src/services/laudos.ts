/** Revisão, liberação de demonstração e arquivamento: o AGHU real não é alterado. */
import api from './api';

export interface ItemRevisao {
  id: number;
  identificador_interno: string;
  solicitacao_aghu: string | number;
  paciente_nome: string;
  tipo_exame: string;
  etapa_atual: string;
  urgente: boolean;
  salvo_por: string;
  salvo_em: string;
  situacao_revisao: 'RASCUNHO' | 'EM_REVISAO';
}
export interface PendenteLiberacao {
  id: number;
  identificador_interno: string;
  solicitacao_aghu: string | number;
  paciente_nome: string;
  tipo_exame: string;
  etapa_atual: string;
  status: 'AGUARDANDO_LIBERACAO' | 'LAUDO_LIBERADO';
  atualizado_em: string;
}
export interface TextoLaudo {
  fase: string;
  tipo: string;
  conteudo: string;
  validado_por: string | null;
  validado_em: string | null;
}
export interface HistoricoLaudo {
  solicitacao_id: number;
  estado: 'ARQUIVADO' | 'LIBERADO' | 'VALIDADO_PENDENTE_AGHU' | 'EM_ANDAMENTO';
  liberacao: {
    fonte: string;
    referencia: string;
    liberado_em: string;
    liberado_por: string;
    arquivado_em: string | null;
    arquivado_por: string | null;
  } | null;
  documentos: TextoLaudo[];
  aviso: string;
}
export async function listarRevisoes(): Promise<ItemRevisao[]> {
  return (await api.get<ItemRevisao[]>('/api/laudos/revisoes')).data;
}
export async function listarPendentesLiberacao(): Promise<PendenteLiberacao[]> {
  return (await api.get<PendenteLiberacao[]>('/api/laudos/pendentes-liberacao')).data;
}
export async function consultarLaudos(id: number): Promise<HistoricoLaudo> {
  return (await api.get<HistoricoLaudo>(`/api/laudos/solicitacoes/${id}`)).data;
}
export async function simularLiberacao(id: number): Promise<HistoricoLaudo> {
  return (await api.post<HistoricoLaudo>(`/api/laudos/solicitacoes/${id}/liberacao-simulada`)).data;
}
export async function arquivarSolicitacao(id: number): Promise<HistoricoLaudo> {
  return (await api.post<HistoricoLaudo>(`/api/laudos/solicitacoes/${id}/arquivar`)).data;
}
