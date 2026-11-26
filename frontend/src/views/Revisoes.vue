<template>
  <div class="space-y-6">
    <p class="text-sm text-gray-600">Rascunhos e pré-laudos pendentes de avaliação clínica. A liberação oficial permanece no AGHU.</p>
    <p v-if="erro" role="alert" class="rounded bg-red-50 p-3 text-sm text-red-700">{{ erro }}</p>
    <p v-if="aviso" role="status" class="rounded bg-green-50 p-3 text-sm text-green-800">{{ aviso }}</p>
    <section class="rounded-lg border border-gray-200 bg-white p-4">
      <div class="mb-3 flex items-center justify-between gap-2">
        <h2 class="text-lg font-semibold">Fila de revisão</h2>
        <Button variant="default" :loading="carregando" @click="carregar">Atualizar</Button>
      </div>
      <p v-if="!carregando && !revisoes.length" class="text-sm text-gray-500">Nenhum rascunho aguardando análise.</p>
      <div v-for="item in revisoes" :key="item.id" class="flex flex-wrap items-center justify-between gap-3 border-t py-3 text-sm">
        <div>
          <p class="font-mono font-semibold">{{ item.identificador_interno }} · AGHU {{ item.solicitacao_aghu }}</p>
          <p>{{ item.paciente_nome }} · {{ rotuloEtapa(item.etapa_atual) }}</p>
          <p class="text-xs text-gray-500">{{ item.situacao_revisao === 'EM_REVISAO' ? 'Pré-laudo para revisão' : 'Rascunho' }} · {{ item.salvo_por }} · {{ formatarDataHora(item.salvo_em) }}</p>
        </div>
        <Button variant="primary" @click="selecionado = item">Abrir formulário</Button>
      </div>
    </section>
    <section class="rounded-lg border border-gray-200 bg-white p-4">
      <h2 class="mb-1 text-lg font-semibold">Laudos validados aguardando liberação ou arquivo</h2>
      <p class="mb-3 text-xs text-gray-500">O evento fictício de liberação só existe no ambiente de demonstração. Não é enviado ao AGHU.</p>
      <p v-if="!carregando && !pendentes.length" class="text-sm text-gray-500">Nenhuma solicitação nesta etapa.</p>
      <div v-for="item in pendentes" :key="item.id" class="flex flex-wrap items-center justify-between gap-3 border-t py-3 text-sm">
        <div>
          <p class="font-mono font-semibold">{{ item.identificador_interno }} · AGHU {{ item.solicitacao_aghu }}</p>
          <p>{{ item.paciente_nome }}</p>
          <p class="text-xs font-medium" :class="item.status === 'LAUDO_LIBERADO' ? 'text-green-700' : 'text-amber-700'">
            {{ item.status === 'LAUDO_LIBERADO' ? 'Liberação fictícia registrada · pronto para arquivar' : 'Aguardando evento de liberação' }}
          </p>
        </div>
        <div class="flex gap-2">
          <Button v-if="podeLiberar && podeSimular && item.status === 'AGUARDANDO_LIBERACAO'" variant="warning" :loading="processando" @click="acao(item.id, 'liberar')">Simular liberação</Button>
          <Button v-if="podeLiberar && podeSimular && item.status === 'LAUDO_LIBERADO'" variant="success" :loading="processando" @click="acao(item.id, 'arquivar')">Arquivar</Button>
        </div>
      </div>
    </section>
    <FormularioFase :show="selecionado !== null" :etapa="selecionado?.etapa_atual || 'MICROSCOPIA'"
      :solicitacao-id="selecionado?.id ?? null" @close="selecionado = null" @alterado="carregar" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import Button from '../components/Button.vue';
import FormularioFase from '../components/FormularioFase.vue';
import { formatarDataHora, mensagemErro, rotuloEtapa } from '../services/solicitacoes';
import { consultarPermissoes } from '../services/permissoes';
import { arquivarSolicitacao, listarPendentesLiberacao, listarRevisoes, simularLiberacao } from '../services/laudos';
import type { ItemRevisao, PendenteLiberacao } from '../services/laudos';
const revisoes = ref<ItemRevisao[]>([]);
const pendentes = ref<PendenteLiberacao[]>([]);
const selecionado = ref<ItemRevisao | null>(null);
const erro = ref('');
const aviso = ref('');
const carregando = ref(false);
const processando = ref(false);
const permissoes = ref<Awaited<ReturnType<typeof consultarPermissoes>> | null>(null);
const podeLiberar = computed(() => !!permissoes.value?.usuario.pode_liberar_laudo);
const podeSimular = computed(() => !!permissoes.value?.simulacao_disponivel);
async function carregar(): Promise<void> {
  carregando.value = true;
  erro.value = '';
  try {
    const [lista, validos, matriz] = await Promise.all([listarRevisoes(), listarPendentesLiberacao(), consultarPermissoes()]);
    revisoes.value = lista; pendentes.value = validos; permissoes.value = matriz;
  } catch (e) { erro.value = mensagemErro(e, 'Não foi possível carregar as filas.'); }
  finally { carregando.value = false; }
}
async function acao(id: number, operacao: 'liberar' | 'arquivar'): Promise<void> {
  if (!window.confirm(operacao === 'liberar' ? 'Registrar evento FICTÍCIO de liberação para esta solicitação?' : 'Confirmar arquivamento?')) return;
  processando.value = true;
  try {
    if (operacao === 'liberar') await simularLiberacao(id); else await arquivarSolicitacao(id);
    aviso.value = operacao === 'liberar' ? 'Evento demonstrativo de liberação registrado.' : 'Solicitação arquivada.';
    await carregar();
  } catch (e) { erro.value = mensagemErro(e); }
  finally { processando.value = false; }
}
onMounted(carregar);
</script>
