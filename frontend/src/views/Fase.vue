<!--
  Fila de uma fase do setor (MVP): Macroscopia, Congelação, Processamento Técnico, IHQ,
  Microscopia e Revisão de Lâmina. A etapa vem de `route.meta.etapa`.

  - Mostra só as solicitações que estão nesta fase agora: urgentes no topo e, depois, da
    entrada na fase mais antiga para a mais recente.
  - Abaixo, na mesma lista, as concluídas nos últimos dias, ainda editáveis.
  - Clicar em "Abrir" mostra o formulário; só o perfil responsável edita.
-->
<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-gray-600">
      <span><strong class="text-gray-800">{{ pendentes }}</strong> pendente(s) nesta fase</span>
      <span v-if="definicao">Edita: <strong class="text-gray-800">{{ quemEdita }}</strong></span>
      <span v-if="definicao">Conclui: <strong class="text-gray-800">{{ quemConclui }}</strong></span>
    </div>

    <!-- Filtros -->
    <div class="grid grid-cols-1 gap-3 rounded-lg border border-gray-200 bg-white p-4 md:grid-cols-12">
      <input
        v-model="filtros.busca"
        class="rounded border p-2 text-sm md:col-span-6"
        placeholder="Prontuário, código AGHU ou código interno"
        @keyup.enter="carregar"
      />
      <select v-model="filtros.tipo_exame" class="rounded border p-2 text-sm md:col-span-4" aria-label="Tipo de exame">
        <option value="">Todos os tipos de exame</option>
        <option v-for="t in TIPOS_EXAME" :key="t.valor" :value="t.valor">{{ t.rotulo }}</option>
      </select>
      <div class="flex gap-2 md:col-span-2">
        <Button variant="primary" :loading="carregando" @click="carregar">Buscar</Button>
      </div>
    </div>

    <p v-if="erro" class="rounded bg-red-50 p-3 text-sm text-red-700" role="alert">{{ erro }}</p>

    <div class="w-full overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b border-gray-200 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500">
            <th class="px-3 py-2">Situação</th>
            <th class="px-3 py-2">Código interno</th>
            <th class="px-3 py-2">Código AGHU</th>
            <th class="px-3 py-2">Paciente</th>
            <th class="px-3 py-2">Prontuário</th>
            <th class="px-3 py-2">Exame</th>
            <th class="px-3 py-2">Amostras</th>
            <th class="px-3 py-2">Na fase desde</th>
            <th class="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="carregando"><td colspan="9" class="px-3 py-4 text-center text-sm text-gray-500">Carregando...</td></tr>
          <tr v-else-if="!itens.length"><td colspan="9" class="px-3 py-6 text-center text-sm text-gray-500">Nenhuma solicitação nesta fase.</td></tr>
          <tr
            v-for="item in itens"
            v-else
            :key="item.id"
            class="align-top text-sm text-gray-700"
            :class="!item.pendente ? 'bg-gray-50 text-gray-500' : item.urgente ? 'bg-red-50/60' : 'hover:bg-gray-50'"
          >
            <td class="px-3 py-3">
              <span v-if="!item.pendente" class="whitespace-nowrap rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">Concluída</span>
              <span v-else-if="item.situacao_fase === 'RASCUNHO'" class="whitespace-nowrap rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">Rascunho salvo</span>
              <span v-else class="whitespace-nowrap rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Pendente</span>
              <span v-if="item.urgente && item.pendente" class="ml-1 whitespace-nowrap rounded bg-red-600 px-1.5 py-0.5 text-[11px] font-bold uppercase text-white">Urgente</span>
              <span v-if="!item.pendente && item.editavel_ate" class="mt-1 block text-xs">editável até {{ formatarDataHora(item.editavel_ate) }}</span>
            </td>
            <td class="px-3 py-3 whitespace-nowrap font-mono font-semibold">{{ item.identificador_interno }}</td>
            <td class="px-3 py-3 font-mono">{{ item.solicitacao_aghu }}</td>
            <td class="px-3 py-3">{{ item.paciente_nome }}</td>
            <td class="px-3 py-3 font-mono">{{ item.prontuario_aghu || '—' }}</td>
            <td class="px-3 py-3">{{ item.tipo_exame }}</td>
            <td class="px-3 py-3">
              <span class="font-semibold">{{ item.qtd_amostras }}</span>
              <span class="block text-xs text-gray-500">{{ item.descricao_amostras || 'Sem descrição no AGHU' }}</span>
            </td>
            <td class="px-3 py-3 whitespace-nowrap">
              <template v-if="item.pendente">{{ formatarDataHora(item.entrou_em) }}</template>
              <template v-else>concluída em {{ formatarDataHora(item.concluido_em) }}</template>
            </td>
            <td class="px-3 py-3 text-right">
              <Button variant="primary" @click="abrir(item.id)">Abrir</Button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="text-xs text-gray-500">
      Concluídas ficam nesta lista por {{ definicao?.dias_edicao_apos_conclusao ?? 6 }} dias para edição e depois saem.
    </p>

    <FormularioFase
      :show="casoAberto !== null"
      :etapa="etapa"
      :caso-id="casoAberto"
      :dias-edicao="definicao?.dias_edicao_apos_conclusao ?? 6"
      @close="casoAberto = null"
      @alterado="carregar"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import Button from '../components/Button.vue';
import FormularioFase from '../components/FormularioFase.vue';
import type { DefinicaoFase, ItemFila } from '../services/fases';
import { listarFases, listarFila } from '../services/fases';
import { TIPOS_EXAME, formatarDataHora, mensagemErro } from '../services/solicitacoes';
import { rotuloPerfil } from '../services/usuarios';

const route = useRoute();
const etapa = computed(() => String(route.meta.etapa || ''));

const definicoes = ref<DefinicaoFase[]>([]);
const definicao = computed(() => definicoes.value.find((d) => d.etapa === etapa.value) ?? null);
const quemEdita = computed(() => (definicao.value?.salvar ?? []).map(rotuloPerfil).join(', '));
const quemConclui = computed(() => (definicao.value?.concluir ?? []).map(rotuloPerfil).join(', '));

const filtros = reactive({ busca: '', tipo_exame: '' });
const itens = ref<ItemFila[]>([]);
const carregando = ref(false);
const erro = ref('');
const casoAberto = ref<number | null>(null);
const pendentes = computed(() => itens.value.filter((i) => i.pendente).length);

/** Carrega a fila da fase com os filtros. */
async function carregar(): Promise<void> {
  if (!etapa.value) return;
  carregando.value = true;
  erro.value = '';
  try {
    if (!definicoes.value.length) definicoes.value = await listarFases();
    itens.value = (await listarFila(etapa.value, filtros, 1, 100)).items;
  } catch (e) {
    erro.value = mensagemErro(e, 'Não foi possível carregar a fila.');
  } finally {
    carregando.value = false;
  }
}

/** Abre o formulário da solicitação. */
function abrir(id: number): void {
  casoAberto.value = id;
}

watch(etapa, () => {
  casoAberto.value = null;
  Object.assign(filtros, { busca: '', tipo_exame: '' });
  carregar();
}, { immediate: true });
</script>
