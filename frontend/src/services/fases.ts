/**
 * Serviço das fases do setor (MVP): fila de cada fase e formulário com Salvar e Concluído.
 *
 * Fala com /api/fases. As definições de campos vêm do backend (provisórias até a reunião com
 * o setor), então a tela não precisa mudar quando os campos mudarem.
 */
import api from './api';

export type TipoCampo = 'texto' | 'texto_longo' | 'numero' | 'sim_nao' | 'opcao';
export type ValorCampo = string | number | boolean | null;

export interface CampoFormulario {
  nome: string;
  rotulo: string;
  tipo: TipoCampo;
  obrigatorio: boolean;
  opcoes?: string[];
  tipos_exame?: string[];
  perfis?: string[];
  /** Presente no formulário de uma solicitação: se o perfil logado pode editar o campo agora. */
  editavel?: boolean;
}

export interface DefinicaoFase {
  etapa: string;
  rotulo: string;
  grupo: 'PRE_ANALITICA' | 'ANALITICA';
  salvar: string[];
  concluir: string[];
  campos: CampoFormulario[];
  dias_edicao_apos_conclusao: number;
}

export interface ItemFila {
  id: number;
  identificador_interno: string;
  solicitacao_aghu: string | number;
  paciente_nome: string;
  prontuario_aghu: string | number | null;
  tipo_exame: string;
  etapa_atual: string;
  urgente: boolean;
  pendente: boolean;
  situacao_fase: 'RASCUNHO' | 'CONCLUIDA' | null;
  entrou_em: string | null;
  salvo_em: string | null;
  salvo_por: string | null;
  concluido_em: string | null;
  concluido_por: string | null;
  editavel_ate: string | null;
  qtd_amostras: number;
  descricao_amostras: string | null;
}

export interface PaginaFila {
  items: ItemFila[];
  total: number;
  pagina: number;
  limite: number;
}

export interface FormularioFase {
  etapa: string;
  rotulo: string;
  solicitacao: {
    id: number;
    identificador_interno: string;
    solicitacao_aghu: string | number;
    paciente_nome: string;
    prontuario_aghu: string | number | null;
    tipo_exame: string;
    etapa_atual: string;
    urgente: boolean;
    amostras: { id: number; amostra_aghu: string | number; descricao?: string | null }[];
  };
  situacao: 'RASCUNHO' | 'CONCLUIDA' | null;
  dados: Record<string, ValorCampo>;
  salvo_por: string | null;
  salvo_em: string | null;
  concluido_por: string | null;
  concluido_em: string | null;
  editavel_ate: string | null;
  pendente: boolean;
  pode_salvar: boolean;
  pode_concluir: boolean;
  campos: CampoFormulario[];
}

/** Definições das fases (rótulos, perfis e campos). */
export async function listarFases(): Promise<DefinicaoFase[]> {
  return (await api.get<DefinicaoFase[]>('/api/fases')).data;
}

/** Fila da fase: pendentes (urgentes no topo, mais antigo primeiro) e concluídas recentes. */
export async function listarFila(
  etapa: string, filtros: { tipo_exame?: string; busca?: string }, pagina = 1, limite = 50,
): Promise<PaginaFila> {
  const params: Record<string, string | number> = { pagina, limite };
  Object.entries(filtros).forEach(([chave, valor]) => {
    if (valor && String(valor).trim()) params[chave] = String(valor).trim();
  });
  return (await api.get<PaginaFila>(`/api/fases/${etapa}/fila`, { params })).data;
}

/** Formulário da fase para a solicitação, com o que o perfil logado pode fazer. */
export async function obterFormulario(etapa: string, id: number): Promise<FormularioFase> {
  return (await api.get<FormularioFase>(`/api/fases/${etapa}/solicitacoes/${id}`)).data;
}

/** Salvar: grava sem exigir os campos obrigatórios. */
export async function salvarFormulario(etapa: string, id: number, dados: Record<string, ValorCampo>): Promise<FormularioFase> {
  return (await api.put<FormularioFase>(`/api/fases/${etapa}/solicitacoes/${id}`, { dados })).data;
}

/** Concluído: exige os obrigatórios e envia a solicitação para a próxima fase. */
export async function concluirFormulario(etapa: string, id: number, dados: Record<string, ValorCampo>): Promise<FormularioFase> {
  return (await api.post<FormularioFase>(`/api/fases/${etapa}/solicitacoes/${id}/concluir`, { dados })).data;
}

/** Valor vazio para o formulário (mesma regra do backend). */
export function vazio(valor: ValorCampo | undefined): boolean {
  return valor === null || valor === undefined || (typeof valor === 'string' && !valor.trim());
}

/** Rótulos dos campos obrigatórios ainda vazios (mesma regra do backend, para avisar antes de enviar). */
export function camposFaltando(campos: CampoFormulario[], dados: Record<string, ValorCampo>): string[] {
  return campos.filter((c) => c.obrigatorio && vazio(dados[c.nome])).map((c) => c.rotulo);
}

/** Só os campos que o perfil pode editar entram no envio; números chegam como número. */
export function dadosParaEnvio(campos: CampoFormulario[], dados: Record<string, ValorCampo>): Record<string, ValorCampo> {
  const saida: Record<string, ValorCampo> = {};
  campos.filter((c) => c.editavel !== false).forEach((c) => {
    const valor = dados[c.nome];
    if (c.tipo === 'numero' && typeof valor === 'string') {
      saida[c.nome] = valor.trim() === '' ? null : Number(valor);
    } else {
      saida[c.nome] = vazio(valor) ? null : (valor as ValorCampo);
    }
  });
  return saida;
}
