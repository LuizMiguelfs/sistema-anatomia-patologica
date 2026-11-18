/**
 * Rótulos em português das ações gravadas na trilha de auditoria.
 *
 * A trilha guarda o código da ação (ex.: `MARCAR_RETIRADO`, `CONCLUIR_MACROSCOPIA`); a tela
 * nunca mostra esse código cru. Ao criar uma ação nova no backend, inclua o rótulo aqui
 * (o spec lista todas as ações conhecidas).
 */
import { ETAPAS, rotuloEtapa } from './solicitacoes';

/** Ações de código fixo, agrupadas pela categoria em que são gravadas. */
export const ACOES_FIXAS: ReadonlyArray<{ categoria: string; valor: string; rotulo: string; legado?: boolean }> = [
  // Segurança
  { categoria: 'SEGURANCA', valor: 'LOGIN', rotulo: 'Entrada no sistema' },
  { categoria: 'SEGURANCA', valor: 'LOGOUT', rotulo: 'Saída do sistema' },
  { categoria: 'SEGURANCA', valor: 'RENOVAR_SESSAO', rotulo: 'Sessão renovada' },
  // Configuração (usuários e perfis)
  { categoria: 'CONFIGURACAO', valor: 'INCLUIR_USUARIO', rotulo: 'Usuário incluído' },
  { categoria: 'CONFIGURACAO', valor: 'ALTERAR_PERFIL_USUARIO', rotulo: 'Perfil de usuário alterado' },
  { categoria: 'CONFIGURACAO', valor: 'INATIVAR_USUARIO', rotulo: 'Acesso de usuário inativado' },
  { categoria: 'CONFIGURACAO', valor: 'REATIVAR_USUARIO', rotulo: 'Acesso de usuário reativado' },
  // Solicitações de exame
  { categoria: 'NEGOCIO_CLINICO', valor: 'ABRIR_SOLICITACAO', rotulo: 'Entrada da solicitação no SAP' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'MARCAR_RETIRADO', rotulo: 'Marcada como retirada' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'DESFAZER_RETIRADA', rotulo: 'Retirada desfeita' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'CONCLUIR_ETAPA', rotulo: 'Etapa concluída' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'ENCAMINHAR_SOLICITACAO', rotulo: 'Encaminhada a outra etapa' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'RETORNAR_SOLICITACAO', rotulo: 'Retornada à etapa de origem' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'SINCRONIZAR_CADASTRO_AGHU', rotulo: 'Cadastro atualizado a partir do AGHU' },
  // Códigos anteriores à T4.1, ainda presentes na trilha (que é imutável); mesmo rótulo dos novos
  { categoria: 'NEGOCIO_CLINICO', valor: 'ABRIR_CASO', rotulo: 'Entrada da solicitação no SAP', legado: true },
  { categoria: 'NEGOCIO_CLINICO', valor: 'ENCAMINHAR_CASO', rotulo: 'Encaminhada a outra etapa', legado: true },
  { categoria: 'NEGOCIO_CLINICO', valor: 'RETORNAR_CASO', rotulo: 'Retornada à etapa de origem', legado: true },
  // Cadastro de pacientes (módulo antigo, ainda gravado na trilha)
  { categoria: 'NEGOCIO_CLINICO', valor: 'CRIAR_PACIENTE', rotulo: 'Paciente cadastrado' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'ALTERAR_PACIENTE', rotulo: 'Cadastro de paciente alterado' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'EXCLUIR_PACIENTE', rotulo: 'Paciente excluído' },
  { categoria: 'NEGOCIO_CLINICO', valor: 'REGISTRAR_ALTA_PACIENTE', rotulo: 'Alta do paciente registrada' },
];

/** Fases que têm formulário (geram SALVAR_, CONCLUIR_ e EDITAR_CONCLUIDA_ + fase). */
export const FASES_COM_FORMULARIO = ['MACROSCOPIA', 'CONGELACAO', 'PROCESSAMENTO', 'IHQ', 'MICROSCOPIA', 'REVISAO'] as const;

/** Ações de formulário: o código é o prefixo + a fase (ex.: SALVAR_MACROSCOPIA). */
const ACOES_DE_FASE: ReadonlyArray<{ prefixo: string; rotulo: (fase: string) => string }> = [
  { prefixo: 'EDITAR_CONCLUIDA_', rotulo: (fase) => `${fase}: editada depois de concluída` },
  { prefixo: 'SALVAR_', rotulo: (fase) => `${fase}: rascunho salvo` },
  { prefixo: 'CONCLUIR_', rotulo: (fase) => `${fase}: fase concluída` },
];

const POR_CODIGO = new Map(ACOES_FIXAS.map((a) => [a.valor, a.rotulo]));

/** "ALGO_NOVO" → "Algo novo": último recurso para uma ação ainda sem rótulo. */
function humanizar(codigo: string): string {
  const texto = codigo.toLowerCase().replace(/_+/g, ' ').trim();
  return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : '—';
}

/** Rótulo em português de uma ação da trilha. Nunca devolve o código cru. */
export function rotuloAcao(acao: string | null | undefined): string {
  const codigo = String(acao ?? '').trim().toUpperCase();
  const fixo = POR_CODIGO.get(codigo);
  if (fixo) return fixo;
  for (const { prefixo, rotulo } of ACOES_DE_FASE) {
    const fase = codigo.startsWith(prefixo) ? codigo.slice(prefixo.length) : '';
    if (fase && fase in ETAPAS) return rotulo(rotuloEtapa(fase));
  }
  return humanizar(codigo);
}

/** Todas as ações conhecidas (fixas + de cada fase). Os códigos legados têm `legado: true`. */
export function acoesConhecidas(): Array<{ categoria: string; valor: string; rotulo: string; legado?: boolean }> {
  const deFase = FASES_COM_FORMULARIO.flatMap((fase) =>
    ['SALVAR_', 'CONCLUIR_', 'EDITAR_CONCLUIDA_'].map((prefixo) => ({
      categoria: 'NEGOCIO_CLINICO', valor: `${prefixo}${fase}`, rotulo: rotuloAcao(`${prefixo}${fase}`),
    })),
  );
  return [...ACOES_FIXAS, ...deFase];
}
