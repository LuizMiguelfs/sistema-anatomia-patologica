import { describe, expect, it } from 'vitest';
import { ACOES_FIXAS, FASES_COM_FORMULARIO, acoesConhecidas, rotuloAcao } from './auditoria';

/**
 * Todas as ações que o backend grava hoje (busca por `acao=` em src/).
 * Criou uma ação nova no backend? Inclua aqui e o rótulo em services/auditoria.ts.
 */
const ACOES_DO_BACKEND = [
  'LOGIN', 'LOGOUT', 'RENOVAR_SESSAO',
  'INCLUIR_USUARIO', 'ALTERAR_PERFIL_USUARIO', 'INATIVAR_USUARIO', 'REATIVAR_USUARIO',
  'ABRIR_SOLICITACAO', 'MARCAR_RETIRADO', 'DESFAZER_RETIRADA', 'CONCLUIR_ETAPA', 'ENCAMINHAR_SOLICITACAO',
  'RETORNAR_SOLICITACAO', 'SINCRONIZAR_CADASTRO_AGHU',
  // anteriores à T4.1, ainda na trilha
  'ABRIR_CASO', 'ENCAMINHAR_CASO', 'RETORNAR_CASO',
  'CRIAR_PACIENTE', 'ALTERAR_PACIENTE', 'EXCLUIR_PACIENTE', 'REGISTRAR_ALTA_PACIENTE',
  ...FASES_COM_FORMULARIO.flatMap((f) => [`SALVAR_${f}`, `CONCLUIR_${f}`, `EDITAR_CONCLUIDA_${f}`]),
];

describe('services/auditoria · rótulos das ações', () => {
  it('toda ação do backend tem rótulo próprio, sem código cru', () => {
    const conhecidas = new Set(acoesConhecidas().map((a) => a.valor));
    for (const acao of ACOES_DO_BACKEND) {
      expect(conhecidas.has(acao), `${acao} sem rótulo`).toBe(true);
      const rotulo = rotuloAcao(acao);
      expect(rotulo).not.toBe(acao);
      expect(rotulo).not.toMatch(/_/);
    }
  });

  it('ações novas do MVP', () => {
    expect(rotuloAcao('MARCAR_RETIRADO')).toBe('Marcada como retirada');
    expect(rotuloAcao('DESFAZER_RETIRADA')).toBe('Retirada desfeita');
    expect(rotuloAcao('SALVAR_MACROSCOPIA')).toBe('Macroscopia: rascunho salvo');
    expect(rotuloAcao('CONCLUIR_PROCESSAMENTO')).toBe('Processamento Técnico: fase concluída');
    expect(rotuloAcao('EDITAR_CONCLUIDA_REVISAO')).toBe('Revisão de Lâmina: editada depois de concluída');
  });

  it('CONCLUIR_ETAPA (rota antiga) não é lida como a fase "ETAPA"', () => {
    expect(rotuloAcao('CONCLUIR_ETAPA')).toBe('Etapa concluída');
  });

  it('não usa o termo "caso" em nenhum rótulo', () => {
    for (const a of acoesConhecidas()) expect(a.rotulo.toLowerCase()).not.toMatch(/\bcaso\b/);
  });

  it('ação desconhecida vira texto legível, nunca o código', () => {
    expect(rotuloAcao('GERAR_ETIQUETA')).toBe('Gerar etiqueta');
    expect(rotuloAcao('salvar_fase_nova')).toBe('Salvar fase nova');
    expect(rotuloAcao('')).toBe('—');
    expect(rotuloAcao(null)).toBe('—');
  });

  it('códigos anteriores à T4.1 têm o mesmo rótulo dos novos e ficam marcados como legados', () => {
    expect(rotuloAcao('ABRIR_CASO')).toBe(rotuloAcao('ABRIR_SOLICITACAO'));
    expect(rotuloAcao('ENCAMINHAR_CASO')).toBe(rotuloAcao('ENCAMINHAR_SOLICITACAO'));
    expect(rotuloAcao('RETORNAR_CASO')).toBe(rotuloAcao('RETORNAR_SOLICITACAO'));
    const legados = acoesConhecidas().filter((a) => a.legado).map((a) => a.valor);
    expect(legados).toEqual(['ABRIR_CASO', 'ENCAMINHAR_CASO', 'RETORNAR_CASO']);
  });

  it('ações fixas não se repetem', () => {
    const valores = ACOES_FIXAS.map((a) => a.valor);
    expect(new Set(valores).size).toBe(valores.length);
  });
});
