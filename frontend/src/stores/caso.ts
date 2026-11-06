import { defineStore } from 'pinia';
import { ref } from 'vue';
import api from '../services/api';

export interface CasoResumo {
  id: number;
  identificador_interno: string;
  solicitacao_aghu: string;
  paciente_nome: string;
  tipo_exame: string;
  etapa_atual: string;
  status: string;
  criado_em: string;
  atualizado_em: string;
}

export interface CasoDetalhe extends CasoResumo {
  prontuario_aghu?: string | null;
  amostras: { id: number; amostra_aghu: string; descricao?: string | null }[];
  acoes: { pode_concluir: boolean; pode_retornar: boolean; destinos_encaminhamento: string[] };
}

export interface Movimentacao {
  id: number;
  tipo: string;
  etapa_origem?: string | null;
  etapa_destino?: string | null;
  motivo?: string | null;
  usuario: string;
  criado_em: string;
}

export interface SolicitacaoAghu {
  solicitacao_aghu: number | string;
  paciente_nome: string;
  prontuario_aghu?: string | null;
  amostras: { amostra_aghu: number | string; descricao?: string | null }[];
  caso_existente: string | null;
}

export interface FiltrosCaso {
  solicitacao?: string;
  /** Prontuário do paciente: busca exata (o nome fica cifrado no banco). */
  prontuario?: string;
  identificador?: string;
  tipo_exame?: string;
  etapa?: string;
  status?: string;
}

/** Extrai a mensagem padrão {"detail": "..."} devolvida pela API. */
export function mensagemErro(error: any, padrao = 'Não foi possível concluir a operação.'): string {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg; // erro de validação (422)
  return padrao;
}

export const useCasoStore = defineStore('caso', () => {
  const casos = ref<CasoResumo[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function buscar(filtros: FiltrosCaso, pagina: number, limite: number) {
    loading.value = true;
    try {
      const params: Record<string, string | number> = { pagina, limite };
      Object.entries(filtros).forEach(([chave, valor]) => {
        if (valor && String(valor).trim()) params[chave] = String(valor).trim();
      });
      const { data } = await api.get('/api/casos', { params });
      casos.value = data.items;
      total.value = data.total;
    } finally {
      loading.value = false;
    }
  }

  const consultarAghu = async (solicitacao: string): Promise<SolicitacaoAghu> =>
    (await api.get(`/api/casos/aghu/solicitacao/${encodeURIComponent(solicitacao)}`)).data;

  const abrir = async (solicitacao: string, tipoExame: string): Promise<CasoDetalhe> =>
    (await api.post('/api/casos', { solicitacao_aghu: solicitacao, tipo_exame: tipoExame })).data;

  const obter = async (id: number): Promise<CasoDetalhe> => (await api.get(`/api/casos/${id}`)).data;

  const historico = async (id: number): Promise<Movimentacao[]> =>
    (await api.get(`/api/casos/${id}/historico`)).data;

  const concluirEtapa = async (id: number): Promise<CasoDetalhe> =>
    (await api.post(`/api/casos/${id}/concluir-etapa`)).data;

  const encaminhar = async (id: number, destino: string, motivo: string): Promise<CasoDetalhe> =>
    (await api.post(`/api/casos/${id}/encaminhar`, { destino, motivo })).data;

  const retornar = async (id: number, motivo: string): Promise<CasoDetalhe> =>
    (await api.post(`/api/casos/${id}/retornar`, { motivo })).data;

  return { casos, total, loading, buscar, consultarAghu, abrir, obter, historico, concluirEtapa, encaminhar, retornar };
});