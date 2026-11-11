<!--
  Formulário de uma fase para uma solicitação (MVP).

  Props: `show`, `etapa`, `casoId`. Eventos: `close` e `alterado` (salvou ou concluiu).
  - Salvar: grava sem exigir obrigatórios.
  - Concluído: confere os obrigatórios (mostra os que faltam), pede confirmação e envia a
    solicitação para a próxima fase.
  - Quem não é o perfil responsável vê tudo em modo somente leitura.
  Os campos vêm do backend (src/helpers/formularios_fase.py).
-->
<template>
  <Modal :show="show" largura="xl" @close="emit('close')">
    <template #header>
      <span v-if="form">
        {{ form.rotulo }} ·
        <span class="font-mono">{{ form.solicitacao.identificador_interno }}</span>
        <span v-if="form.solicitacao.urgente" class="ml-2 rounded bg-red-600 px-1.5 py-0.5 align-middle text-xs font-bold uppercase text-white">Urgente</span>
      </span>
      <span v-else>Formulário da fase</span>
    </template>

    <p v-if="carregando" class="text-sm text-gray-500">Carregando...</p>
    <div v-else-if="form" class="space-y-5 text-sm">
      <!-- Dados da solicitação (AGHU, somente leitura) -->
      <div class="grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg border border-gray-200 bg-gray-50 p-3 md:grid-cols-3">
        <p><span class="text-gray-500">Código AGHU:</span> <span class="font-mono">{{ form.solicitacao.solicitacao_aghu }}</span></p>
        <p><span class="text-gray-500">Prontuário:</span> <span class="font-mono">{{ form.solicitacao.prontuario_aghu || '—' }}</span></p>
        <p><span class="text-gray-500">Exame:</span> {{ form.solicitacao.tipo_exame }}</p>
        <p class="col-span-2 md:col-span-3"><span class="text-gray-500">Paciente:</span> {{ form.solicitacao.paciente_nome }}</p>
        <p class="col-span-2 md:col-span-3">
          <span class="text-gray-500">Amostras ({{ form.solicitacao.amostras.length }}):</span>
          {{ form.solicitacao.amostras.map(a => a.descricao || `Amostra ${a.amostra_aghu}`).join('; ') || '—' }}
        </p>
      </div>

      <!-- Situação do formulário -->
      <div class="rounded-lg p-3" :class="situacaoClasse">
        <p class="font-medium">{{ situacaoTexto }}</p>
        <p v-if="!form.pode_salvar" class="text-xs">Seu perfil só visualiza esta fase.</p>
      </div>

      <p v-if="erro" class="rounded bg-red-50 p-3 text-red-700" role="alert">{{ erro }}</p>
      <div v-if="faltando.length" class="rounded border border-amber-300 bg-amber-50 p-3 text-amber-900" role="alert">
        <p class="font-medium">Preencha os campos obrigatórios para concluir:</p>
        <ul class="ml-5 list-disc">
          <li v-for="f in faltando" :key="f">{{ f }}</li>
        </ul>
      </div>
      <p v-if="aviso" class="rounded bg-green-50 p-3 text-green-800" role="status">{{ aviso }}</p>

      <!-- Campos -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          v-for="campo in form.campos"
          :key="campo.nome"
          :class="campo.tipo === 'texto_longo' ? 'md:col-span-2' : ''"
        >
          <label :for="`campo-${campo.nome}`" class="mb-1 block font-medium text-gray-700">
            {{ campo.rotulo }}<span v-if="campo.obrigatorio" class="text-red-600"> *</span>
          </label>

          <textarea
            v-if="campo.tipo === 'texto_longo'"
            :id="`campo-${campo.nome}`"
            :value="textoDe(campo.nome)"
            @input="atualizar(campo.nome, $event)"
            rows="3"
            :disabled="!campo.editavel"
            class="w-full rounded border p-2 disabled:bg-gray-100 disabled:text-gray-600"
            :class="destaque(campo.rotulo)"
          ></textarea>
          <input
            v-else-if="campo.tipo === 'texto'"
            :id="`campo-${campo.nome}`"
            :value="textoDe(campo.nome)"
            @input="atualizar(campo.nome, $event)"
            :disabled="!campo.editavel"
            class="w-full rounded border p-2 disabled:bg-gray-100 disabled:text-gray-600"
            :class="destaque(campo.rotulo)"
          />
          <input
            v-else-if="campo.tipo === 'numero'"
            :id="`campo-${campo.nome}`"
            :value="textoDe(campo.nome)"
            @input="atualizar(campo.nome, $event)"
            type="number"
            min="0"
            :disabled="!campo.editavel"
            class="w-full rounded border p-2 disabled:bg-gray-100 disabled:text-gray-600"
            :class="destaque(campo.rotulo)"
          />
          <select
            v-else-if="campo.tipo === 'opcao'"
            :id="`campo-${campo.nome}`"
            v-model="dados[campo.nome]"
            :disabled="!campo.editavel"
            class="w-full rounded border p-2 disabled:bg-gray-100 disabled:text-gray-600"
            :class="destaque(campo.rotulo)"
          >
            <option :value="null">Selecione</option>
            <option v-for="o in campo.opcoes" :key="o" :value="o">{{ o }}</option>
          </select>
          <div v-else-if="campo.tipo === 'sim_nao'" :id="`campo-${campo.nome}`" class="flex gap-4 rounded border p-2" :class="destaque(campo.rotulo)">
            <label class="flex items-center gap-1"><input v-model="dados[campo.nome]" type="radio" :value="true" :disabled="!campo.editavel" /> Sim</label>
            <label class="flex items-center gap-1"><input v-model="dados[campo.nome]" type="radio" :value="false" :disabled="!campo.editavel" /> Não</label>
          </div>

          <p v-if="campo.perfis && !campo.editavel && form.pode_salvar" class="mt-1 text-xs text-gray-500">Preenchido pelo patologista (Preceptoria).</p>
        </div>
      </div>
      <p class="text-xs text-gray-500">* Obrigatório para concluir. Formulário provisório: os campos finais serão definidos com o setor.</p>
    </div>

    <template #footer>
      <Button variant="default" @click="emit('close')">Fechar</Button>
      <Button v-if="form?.pode_salvar" variant="info" :loading="salvando" @click="salvar">Salvar</Button>
      <Button v-if="form?.pode_concluir" variant="success" :loading="concluindo" @click="pedirConclusao">Concluído</Button>
    </template>
  </Modal>

  <!-- Confirmação de conclusão -->
  <Modal :show="confirmando" @close="confirmando = false">
    <template #header>Concluir {{ form?.rotulo }}</template>
    <p class="text-sm">
      Concluir a fase {{ form?.rotulo }} da solicitação
      <strong class="font-mono">{{ form?.solicitacao.identificador_interno }}</strong>?
      Ela seguirá na hora para a próxima fase. Você ainda poderá editar este formulário por
      {{ diasEdicao }} dias.
    </p>
    <template #footer>
      <Button variant="default" @click="confirmando = false">Cancelar</Button>
      <Button variant="success" :loading="concluindo" @click="concluir">Confirmar conclusão</Button>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { PropType } from 'vue';
import Button from './Button.vue';
import Modal from './Modal.vue';
import type { FormularioFase, ValorCampo } from '../services/fases';
import {
  camposFaltando, concluirFormulario, dadosParaEnvio, obterFormulario, salvarFormulario,
} from '../services/fases';
import { formatarDataHora, mensagemErro } from '../services/solicitacoes';

const props = defineProps({
  show: { type: Boolean, default: false },
  etapa: { type: String, required: true },
  casoId: { type: Number as PropType<number | null>, default: null },
  diasEdicao: { type: Number, default: 6 },
});
const emit = defineEmits(['close', 'alterado']);

const form = ref<FormularioFase | null>(null);
const dados = ref<Record<string, ValorCampo>>({});
const carregando = ref(false);
const salvando = ref(false);
const concluindo = ref(false);
const confirmando = ref(false);
const erro = ref('');
const aviso = ref('');
const faltando = ref<string[]>([]);

const situacaoTexto = computed(() => {
  const f = form.value;
  if (!f) return '';
  if (f.situacao === 'CONCLUIDA') {
    const ate = f.editavel_ate ? ` Editável até ${formatarDataHora(f.editavel_ate)}.` : '';
    return `Concluída por ${f.concluido_por} em ${formatarDataHora(f.concluido_em)}.${ate}`;
  }
  if (f.situacao === 'RASCUNHO') return `Pendente · salvo por ${f.salvo_por} em ${formatarDataHora(f.salvo_em)}.`;
  return 'Pendente · nada registrado ainda nesta fase.';
});
const situacaoClasse = computed(() => (form.value?.situacao === 'CONCLUIDA'
  ? 'bg-green-50 text-green-900' : 'bg-blue-50 text-blue-900'));

/** Valor do campo como texto para inputs e textareas. */
function textoDe(nome: string): string {
  const valor = dados.value[nome];
  return valor === null || valor === undefined ? '' : String(valor);
}

/** Atualiza o campo a partir de um input ou textarea. */
function atualizar(nome: string, evento: Event): void {
  dados.value[nome] = (evento.target as HTMLInputElement | HTMLTextAreaElement).value;
}

/** Borda de alerta nos obrigatórios que faltam. */
function destaque(rotulo: string): string {
  return faltando.value.includes(rotulo) ? 'border-amber-500 ring-1 ring-amber-400' : 'border-gray-300';
}

/** Carrega o formulário da solicitação. */
async function carregar(): Promise<void> {
  if (!props.casoId) return;
  carregando.value = true;
  erro.value = '';
  aviso.value = '';
  faltando.value = [];
  try {
    aplicar(await obterFormulario(props.etapa, props.casoId));
  } catch (e) {
    form.value = null;
    erro.value = mensagemErro(e, 'Não foi possível abrir o formulário.');
  } finally {
    carregando.value = false;
  }
}

/** Aplica a resposta da API na tela (cópia editável dos dados). */
function aplicar(resposta: FormularioFase): void {
  form.value = resposta;
  const copia: Record<string, ValorCampo> = {};
  resposta.campos.forEach((c) => { copia[c.nome] = resposta.dados[c.nome] ?? null; });
  dados.value = copia;
}

/** Salvar: sem exigir obrigatórios. */
async function salvar(): Promise<void> {
  if (!form.value || !props.casoId) return;
  salvando.value = true;
  erro.value = '';
  aviso.value = '';
  faltando.value = [];
  try {
    aplicar(await salvarFormulario(props.etapa, props.casoId, dadosParaEnvio(form.value.campos, dados.value)));
    aviso.value = 'Formulário salvo.';
    emit('alterado');
  } catch (e) {
    erro.value = mensagemErro(e, 'Não foi possível salvar.');
  } finally {
    salvando.value = false;
  }
}

/** Concluído: confere os obrigatórios antes de pedir confirmação. */
function pedirConclusao(): void {
  if (!form.value) return;
  aviso.value = '';
  erro.value = '';
  faltando.value = camposFaltando(form.value.campos, dados.value);
  if (!faltando.value.length) confirmando.value = true;
}

/** Envia a conclusão; a solicitação segue para a próxima fase. */
async function concluir(): Promise<void> {
  if (!form.value || !props.casoId) return;
  concluindo.value = true;
  try {
    aplicar(await concluirFormulario(props.etapa, props.casoId, dadosParaEnvio(form.value.campos, dados.value)));
    confirmando.value = false;
    aviso.value = 'Fase concluída. A solicitação seguiu para a próxima fase.';
    emit('alterado');
  } catch (e) {
    confirmando.value = false;
    erro.value = mensagemErro(e, 'Não foi possível concluir.');
  } finally {
    concluindo.value = false;
  }
}

watch(() => [props.show, props.casoId], () => { if (props.show) carregar(); }, { immediate: true });
</script>
