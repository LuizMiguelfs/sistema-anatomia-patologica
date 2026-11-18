/**
 * Retrato das filas no Início (T5.1): tipos do `filas` de GET /api/dashboard/resumo e o
 * caminho de cada número até a aba onde estão as solicitações contadas.
 */

export interface FilaFase {
  etapa: string;
  rotulo: string;
  grupo: 'PRE_ANALITICA' | 'ANALITICA' | string;
  pendentes: number;
  urgentes: number;
  /** Só nas fases com pré-laudo (Congelação, Microscopia, Revisão de Lâmina). */
  aguardando_patologista: number | null;
}

export interface RetratoFilas {
  nao_retiradas: number;
  nao_retiradas_urgentes: number;
  urgentes: number;
  aguardando_patologista: number;
  fases: FilaFase[];
}

/** Um número do painel e a aba que ele abre. */
export interface LocalNaFila {
  rotulo: string;
  quantidade: number;
  rota: string;
}

export const ROTA_NAO_RETIRADAS = '/solicitacoes/nao-retirados';

/** Aba de cada fase (as mesmas rotas do menu). */
export const ROTAS_DAS_FASES: Readonly<Record<string, string>> = {
  MACROSCOPIA: '/fases/macroscopia',
  CONGELACAO: '/fases/congelacao',
  PROCESSAMENTO: '/fases/processamento',
  IHQ: '/fases/ihq',
  MICROSCOPIA: '/fases/microscopia',
  REVISAO: '/fases/revisao-de-lamina',
};

/** Aba da fase; se a fase for desconhecida, o Início. */
export function rotaDaFase(etapa: string): string {
  return ROTAS_DAS_FASES[etapa] ?? '/';
}

/** Fases de um grupo do menu (Pré-Analítica ou Analítica), na ordem do menu. */
export function fasesDoGrupo(filas: RetratoFilas, grupo: string): FilaFase[] {
  return filas.fases.filter((f) => f.grupo === grupo);
}

/** Onde estão as urgentes: não retiradas e cada fase com urgente, cada uma com sua aba. */
export function locaisComUrgentes(filas: RetratoFilas): LocalNaFila[] {
  const locais: LocalNaFila[] = [];
  if (filas.nao_retiradas_urgentes > 0) {
    locais.push({ rotulo: 'Não retiradas', quantidade: filas.nao_retiradas_urgentes, rota: ROTA_NAO_RETIRADAS });
  }
  filas.fases
    .filter((f) => f.urgentes > 0)
    .forEach((f) => locais.push({ rotulo: f.rotulo, quantidade: f.urgentes, rota: rotaDaFase(f.etapa) }));
  return locais;
}

/** Fases com pré-laudo salvo esperando o patologista validar e concluir. */
export function locaisAguardandoPatologista(filas: RetratoFilas): LocalNaFila[] {
  return filas.fases
    .filter((f) => (f.aguardando_patologista ?? 0) > 0)
    .map((f) => ({ rotulo: f.rotulo, quantidade: f.aguardando_patologista ?? 0, rota: rotaDaFase(f.etapa) }));
}
