<!--
  Linha do tempo de uma solicitação de exame (T2.1): o que foi feito, por quem e quando,
  do primeiro ao último registro. Lê a trilha de auditoria; todos os perfis veem.

  Props: `solicitacaoId` e `versao` (mude o número para recarregar, ex.: depois de salvar).
-->
<template>
  <section class="rounded-lg border border-gray-200">
    <button
      type="button"
      class="flex w-full items-center justify-between px-3 py-2 text-left font-medium text-gray-700"
      :aria-expanded="aberta"
      @click="aberta = !aberta"
    >
      <span>Histórico da solicitação<span v-if="itens.length" class="font-normal text-gray-500"> · {{ itens.length }} registro(s)</span></span>
      <ChevronDownIcon class="h-4 w-4 transition-transform" :class="aberta ? 'rotate-180' : ''" />
    </button>

    <div v-if="aberta" class="border-t border-gray-200 px-3 py-3">
      <p v-if="carregando" class="text-sm text-gray-500">Carregando histórico...</p>
      <p v-else-if="erro" class="text-sm text-red-700" role="alert">{{ erro }}</p>
      <p v-else-if="!itens.length" class="text-sm text-gray-500">Nenhum registro ainda.</p>
      <ol v-else class="relative ml-2 space-y-3 border-l border-gray-200 pl-4">
        <li v-for="item in itens" :key="item.id" class="relative">
          <span class="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-paper-primary" aria-hidden="true"></span>
          <p class="text-sm font-medium text-gray-800">{{ item.titulo }}</p>
          <p class="text-xs text-gray-500">
            {{ formatarDataHora(item.quando) }} · <span class="font-mono">{{ item.usuario }}</span>
            <template v-if="item.detalhe"> · {{ item.detalhe }}</template>
          </p>
        </li>
      </ol>
      <p v-if="incompleta" class="mt-2 text-xs text-gray-500">Mostrando os {{ itens.length }} registros mais recentes de {{ total }}.</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ChevronDownIcon } from '@heroicons/vue/24/outline';
import { listarHistorico, montarLinhaDoTempo, type ItemLinhaDoTempo } from '../services/historico';
import { formatarDataHora, mensagemErro } from '../services/solicitacoes';

const props = defineProps({
  solicitacaoId: { type: Number, required: true },
  versao: { type: Number, default: 0 },
});

const aberta = ref(true);
const itens = ref<ItemLinhaDoTempo[]>([]);
const total = ref(0);
const carregando = ref(false);
const erro = ref('');
const incompleta = computed(() => total.value > itens.value.length);
let requisicao = 0;

/** Busca o histórico; respostas antigas (troca rápida de solicitação) são descartadas. */
async function carregar(): Promise<void> {
  const id = ++requisicao;
  carregando.value = true;
  erro.value = '';
  try {
    const pagina = await listarHistorico(props.solicitacaoId);
    if (id !== requisicao) return;
    itens.value = montarLinhaDoTempo(pagina.itens);
    total.value = pagina.total;
  } catch (e) {
    if (id === requisicao) erro.value = mensagemErro(e, 'Não foi possível carregar o histórico.');
  } finally {
    if (id === requisicao) carregando.value = false;
  }
}

watch(() => [props.solicitacaoId, props.versao], carregar, { immediate: true });
</script>
