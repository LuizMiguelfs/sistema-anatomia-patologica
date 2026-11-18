// @vitest-environment jsdom
/**
 * Testes de componente do formulário da fase (T3.2).
 * As chamadas à API são simuladas; as regras de obrigatórios e de envio são as reais.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import type { CampoFormulario, FormularioFase as Formulario } from '../services/fases';

const obterFormulario = vi.fn();
const salvarFormulario = vi.fn();
const concluirFormulario = vi.fn();
vi.mock('../services/fases', async (original) => ({
  ...(await original<typeof import('../services/fases')>()),
  obterFormulario: (...a: unknown[]) => obterFormulario(...a),
  salvarFormulario: (...a: unknown[]) => salvarFormulario(...a),
  concluirFormulario: (...a: unknown[]) => concluirFormulario(...a),
}));
vi.mock('../services/api', () => ({ default: { get: vi.fn(), put: vi.fn(), post: vi.fn() } }));

import FormularioFase from './FormularioFase.vue';

const CAMPOS_MICROSCOPIA: CampoFormulario[] = [
  { nome: 'pre_laudo', rotulo: 'Pré-laudo', tipo: 'texto_longo', obrigatorio: true },
  { nome: 'diagnostico', rotulo: 'Diagnóstico', tipo: 'texto_longo', obrigatorio: true, perfis: ['PRECEPTORIA'] },
  { nome: 'qtd_laminas', rotulo: 'Nº de lâminas', tipo: 'numero', obrigatorio: false },
];

/** Resposta da API para uma solicitação pendente em Microscopia. */
function formulario(extra: Partial<Formulario> = {}, editavel: Record<string, boolean> = {}): Formulario {
  return {
    etapa: 'MICROSCOPIA',
    rotulo: 'Microscopia',
    solicitacao: {
      id: 7, identificador_interno: 'HP-0007/26', solicitacao_aghu: 500007, paciente_nome: 'PACIENTE FICTICIO',
      prontuario_aghu: '90007', tipo_exame: 'HP', etapa_atual: 'MICROSCOPIA', urgente: false,
      amostras: [{ id: 1, amostra_aghu: 1, descricao: 'Amostra fictícia' }],
    },
    situacao: null, dados: {}, salvo_por: null, salvo_em: null, concluido_por: null, concluido_em: null,
    editavel_ate: null, pendente: true, pode_salvar: true, pode_concluir: true,
    campos: CAMPOS_MICROSCOPIA.map((c) => ({ ...c, editavel: editavel[c.nome] ?? true })),
    ...extra,
  };
}

async function montar(resposta: Formulario) {
  obterFormulario.mockResolvedValue(resposta);
  const wrapper = mount(FormularioFase, {
    props: { show: true, etapa: 'MICROSCOPIA', casoId: 7 },
    // Modal usa teleport; a linha do tempo (quando existir) não é o foco aqui.
    global: { stubs: { teleport: true, LinhaDoTempo: true } },
  });
  await flushPromises();
  return wrapper;
}

const botao = (w: Awaited<ReturnType<typeof montar>>, texto: string) =>
  w.findAll('button').find((b) => b.text().trim() === texto);

describe('FormularioFase', () => {
  beforeEach(() => {
    obterFormulario.mockReset();
    salvarFormulario.mockReset();
    concluirFormulario.mockReset();
  });
  afterEach(() => vi.clearAllMocks());

  it('carrega o formulário da solicitação aberta', async () => {
    const w = await montar(formulario());
    expect(obterFormulario).toHaveBeenCalledWith('MICROSCOPIA', 7);
    expect(w.text()).toContain('HP-0007/26');
    expect(w.text()).toContain('Pendente · nada registrado ainda nesta fase.');
  });

  it('Concluído com obrigatórios vazios lista o que falta e não envia', async () => {
    const w = await montar(formulario());
    await botao(w, 'Concluído')!.trigger('click');

    const aviso = w.find('[role="alert"]');
    expect(aviso.text()).toContain('Preencha os campos obrigatórios para concluir');
    expect(aviso.findAll('li').map((li) => li.text())).toEqual(['Pré-laudo', 'Diagnóstico']);
    expect(w.text()).not.toContain('Confirmar conclusão');
    expect(concluirFormulario).not.toHaveBeenCalled();
    // Os campos que faltam ganham destaque.
    expect(w.find('#campo-pre_laudo').classes()).toContain('border-amber-500');
  });

  it('Concluído com tudo preenchido pede confirmação e só então envia', async () => {
    const preenchido = formulario({ dados: { pre_laudo: 'Texto fictício', diagnostico: 'Texto fictício' } });
    concluirFormulario.mockResolvedValue({ ...preenchido, situacao: 'CONCLUIDA', concluido_por: 'dora.pat', concluido_em: '2026-11-18T12:00:00Z' });
    const w = await montar(preenchido);

    await botao(w, 'Concluído')!.trigger('click');
    expect(concluirFormulario).not.toHaveBeenCalled();
    expect(w.text()).toContain('Confirmar conclusão');

    await botao(w, 'Confirmar conclusão')!.trigger('click');
    await flushPromises();
    expect(concluirFormulario).toHaveBeenCalledWith('MICROSCOPIA', 7, { pre_laudo: 'Texto fictício', diagnostico: 'Texto fictício', qtd_laminas: null });
    expect(w.emitted('alterado')).toHaveLength(1);
    expect(w.text()).toContain('Fase concluída. A solicitação seguiu para a próxima fase.');
  });

  it('Salvar grava sem exigir os obrigatórios', async () => {
    salvarFormulario.mockImplementation(async (_e, _id, dados) => formulario({ situacao: 'RASCUNHO', dados, salvo_por: 'caio.res', salvo_em: '2026-11-18T12:00:00Z' }));
    const w = await montar(formulario());
    await w.find('#campo-qtd_laminas').setValue('3');
    await botao(w, 'Salvar')!.trigger('click');
    await flushPromises();

    expect(salvarFormulario).toHaveBeenCalledWith('MICROSCOPIA', 7, { pre_laudo: null, diagnostico: null, qtd_laminas: 3 });
    expect(w.find('[role="alert"]').exists()).toBe(false);
    expect(w.text()).toContain('Formulário salvo.');
  });

  it('quem só visualiza vê os campos travados e nenhum botão de ação', async () => {
    const w = await montar(formulario(
      { pode_salvar: false, pode_concluir: false, dados: { pre_laudo: 'Texto do residente' } },
      { pre_laudo: false, diagnostico: false, qtd_laminas: false },
    ));
    for (const campo of CAMPOS_MICROSCOPIA) {
      expect(w.find(`#campo-${campo.nome}`).attributes('disabled'), campo.nome).toBeDefined();
    }
    expect((w.find('#campo-pre_laudo').element as HTMLTextAreaElement).value).toBe('Texto do residente');
    expect(w.text()).toContain('Seu perfil só visualiza esta fase.');
    expect(botao(w, 'Salvar')).toBeUndefined();
    expect(botao(w, 'Concluído')).toBeUndefined();
  });

  it('Residentes: diagnóstico travado, demais campos liberados, e o diagnóstico não é enviado', async () => {
    salvarFormulario.mockImplementation(async (_e, _id, dados) => formulario({ situacao: 'RASCUNHO', dados }, { diagnostico: false }));
    const w = await montar(formulario({ pode_concluir: false }, { diagnostico: false }));

    expect(w.find('#campo-diagnostico').attributes('disabled')).toBeDefined();
    expect(w.find('#campo-pre_laudo').attributes('disabled')).toBeUndefined();
    expect(w.find('#campo-qtd_laminas').attributes('disabled')).toBeUndefined();
    expect(w.text()).toContain('Preenchido pelo patologista (Preceptoria).');
    expect(botao(w, 'Salvar')).toBeDefined();
    expect(botao(w, 'Concluído')).toBeUndefined();

    await w.find('#campo-pre_laudo').setValue('Pré-laudo fictício');
    await botao(w, 'Salvar')!.trigger('click');
    await flushPromises();
    const enviado = salvarFormulario.mock.calls[0][2];
    expect(enviado).toEqual({ pre_laudo: 'Pré-laudo fictício', qtd_laminas: null });
    expect(enviado).not.toHaveProperty('diagnostico');
  });

  it('erro da API aparece na tela', async () => {
    concluirFormulario.mockRejectedValue({ response: { data: { detail: 'Preencha os campos obrigatórios: Diagnóstico' } } });
    const w = await montar(formulario({ dados: { pre_laudo: 'x', diagnostico: 'y' } }));
    await botao(w, 'Concluído')!.trigger('click');
    await botao(w, 'Confirmar conclusão')!.trigger('click');
    await flushPromises();
    expect(w.find('[role="alert"]').text()).toContain('Preencha os campos obrigatórios: Diagnóstico');
    expect(w.emitted('alterado')).toBeUndefined();
  });
});
