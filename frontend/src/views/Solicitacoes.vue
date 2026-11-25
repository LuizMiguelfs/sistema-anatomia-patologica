<!--
  Solicitações de Exames (MVP): abas "Não retirados", "Retirados" e "Arquivados" (em breve).

  - Não retirados: urgentes no topo; depois do recebimento mais antigo para o mais recente.
  - Retirados: da retirada mais recente para a mais antiga.
  - Só a Recepção marca (ou desfaz) a retirada, sempre com confirmação; o backend registra e audita.
  - A Recepção abre no SAP uma solicitação recebida no AGHU: digita o número, confere a prévia (tipo,
    origem, status, data e amostras com ID) e confirma. Com pendência (ex.: tipos conflitantes), não abre.
  A aba vem de `route.meta.situacao`.
-->
<template>
  <div class="space-y-5">
    <!-- Abas -->
    <nav class="flex gap-1 border-b border-gray-200" aria-label="Abas de solicitações">
      <router-link
        v-for="aba in ABAS"
        :key="aba.rota"
        :to="aba.rota"
        class="-mb-px border-b-2 px-4 py-2 text-sm font-medium"
        :class="aba.situacao === situacao ? 'border-paper-primary text-paper-primary' : 'border-transparent text-gray-500 hover:text-gray-700'"
      >
        {{ aba.rotulo }}
      </router-link>
    </nav>

    <!-- Arquivados: previsto, ainda não implementado no MVP -->
    <div v-if="situacao === 'ARQUIVADO'" class="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
      <p class="text-lg font-semibold text-gray-700">Em breve</p>
      <p class="mt-1 text-sm text-gray-500">A aba de solicitações arquivadas (do arquivamento mais recente para o mais antigo) faz parte das próximas entregas.</p>
    </div>

    <template v-else>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p class="text-sm text-gray-600">{{ descricaoAba }}</p>
        <Button v-if="ehRecepcao && situacao === 'NAO_RETIRADO'" variant="primary" @click="abrirModalAghu">
          Abrir solicitação do AGHU
        </Button>
      </div>

      <!-- Filtros -->
      <div class="grid grid-cols-1 gap-3 rounded-lg border border-gray-200 bg-white p-4 md:grid-cols-12">
        <input
          v-model="filtros.busca"
          class="rounded border p-2 text-sm md:col-span-4"
          placeholder="Prontuário, código AGHU ou código interno"
          @keyup.enter="pesquisar(1)"
        />
        <select v-model="filtros.tipo_exame" class="rounded border p-2 text-sm md:col-span-3" aria-label="Tipo de exame">
          <option value="">Todos os tipos de exame</option>
          <option v-for="t in TIPOS_EXAME" :key="t.valor" :value="t.valor">{{ t.rotulo }}</option>
        </select>
        <div class="flex items-center gap-2 text-sm text-gray-600 md:col-span-4">
          <span class="shrink-0">{{ situacao === 'RETIRADO' ? 'Retirado entre' : 'Recebido entre' }}</span>
          <input v-model="filtros.de" type="date" class="min-w-0 flex-1 rounded border p-2 text-sm" aria-label="Data inicial" />
          <span class="shrink-0">e</span>
          <input v-model="filtros.ate" type="date" class="min-w-0 flex-1 rounded border p-2 text-sm" aria-label="Data final" />
        </div>
        <div class="flex gap-2 md:col-span-1">
          <Button variant="primary" :loading="carregando" @click="pesquisar(1)">Buscar</Button>
        </div>
        <div class="md:col-span-12">
          <button class="text-sm text-paper-primary hover:underline" @click="limpar">Limpar filtros</button>
        </div>
      </div>

      <p v-if="erro" class="rounded bg-red-50 p-3 text-sm text-red-700" role="alert">{{ erro }}</p>
      <p v-if="aviso" class="rounded bg-green-50 p-3 text-sm text-green-800" role="status">{{ aviso }}</p>

      <!-- Lista -->
      <div class="w-full overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table class="w-full text-left">
          <thead>
            <tr class="border-b border-gray-200 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500">
              <th class="px-3 py-2">Código interno</th>
              <th class="px-3 py-2">Código AGHU</th>
              <th class="px-3 py-2">Paciente</th>
              <th class="px-3 py-2">Prontuário</th>
              <th class="px-3 py-2">Exame</th>
              <th class="px-3 py-2">Amostras</th>
              <th class="px-3 py-2">{{ situacao === 'RETIRADO' ? 'Retirado em' : 'Recebido em' }}</th>
              <th v-if="situacao === 'RETIRADO'" class="px-3 py-2">Fase atual</th>
              <th v-if="ehRecepcao" class="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="carregando"><td :colspan="colunas" class="px-3 py-4 text-center text-sm text-gray-500">Carregando...</td></tr>
            <tr v-else-if="!itens.length"><td :colspan="colunas" class="px-3 py-6 text-center text-sm text-gray-500">Nenhuma solicitação encontrada.</td></tr>
            <tr
              v-for="s in itens"
              v-else
              :key="s.id"
              class="align-top text-sm text-gray-700"
              :class="s.urgente && situacao === 'NAO_RETIRADO' ? 'bg-red-50/60' : 'hover:bg-gray-50'"
            >
              <td class="px-3 py-3 whitespace-nowrap">
                <span class="whitespace-nowrap font-mono font-semibold">{{ s.identificador_interno }}</span>
                <span v-if="s.urgente" class="ml-2 rounded bg-red-600 px-1.5 py-0.5 text-[11px] font-bold uppercase text-white">Urgente</span>
              </td>
              <td class="px-3 py-3 font-mono">{{ s.solicitacao_aghu }}</td>
              <td class="px-3 py-3">{{ s.paciente_nome }}</td>
              <td class="px-3 py-3 font-mono">{{ s.prontuario_aghu || '—' }}</td>
              <td class="px-3 py-3">{{ s.tipo_exame }}</td>
              <td class="px-3 py-3">
                <span class="font-semibold">{{ s.qtd_amostras }}</span>
                <span class="block text-xs text-gray-500">{{ s.descricao_amostras || 'Sem descrição no AGHU' }}</span>
              </td>
              <td class="px-3 py-3 whitespace-nowrap">
                {{ formatarDataHora(situacao === 'RETIRADO' ? s.retirado_em : s.criado_em) }}
                <span v-if="situacao === 'RETIRADO' && s.retirado_por" class="block text-xs text-gray-500">por {{ s.retirado_por }}</span>
              </td>
              <td v-if="situacao === 'RETIRADO'" class="px-3 py-3">{{ rotuloEtapa(s.etapa_atual) }}</td>
              <td v-if="ehRecepcao" class="px-3 py-3 text-right">
                <Button v-if="situacao === 'NAO_RETIRADO'" variant="primary" @click="pedirConfirmacao(s, 'retirar')">Marcar como retirado</Button>
                <Button v-else variant="default" @click="pedirConfirmacao(s, 'desfazer')">Desfazer</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex items-center justify-between text-sm text-gray-600">
        <span>{{ total }} solicitação(ões) · página {{ pagina }} de {{ totalPaginas }}</span>
        <div class="flex gap-2">
          <Button variant="default" :disabled="pagina <= 1 || carregando" @click="pesquisar(pagina - 1)">Anterior</Button>
          <Button variant="default" :disabled="pagina >= totalPaginas || carregando" @click="pesquisar(pagina + 1)">Próxima</Button>
        </div>
      </div>
    </template>

    <!-- Abrir solicitação do AGHU (Recepção) -->
    <Modal :show="modalAghu" largura="xl" @close="fecharModalAghu">
      <template #header>Abrir solicitação do AGHU</template>
      <div class="space-y-4 text-sm">
        <form class="flex gap-2" @submit.prevent="consultarAghu">
          <input
            v-model="numeroAghu"
            class="min-w-0 flex-1 rounded border p-2 font-mono"
            inputmode="numeric"
            placeholder="Número da solicitação no AGHU"
            aria-label="Número da solicitação no AGHU"
          />
          <Button variant="default" type="submit" :loading="consultando">Consultar</Button>
        </form>

        <p v-if="erroAghu" class="rounded bg-red-50 p-3 text-red-700" role="alert">{{ erroAghu }}</p>

        <template v-if="previa">
          <div class="grid grid-cols-2 gap-x-4 gap-y-1 rounded border border-gray-200 bg-gray-50 p-3 md:grid-cols-3">
            <p><span class="text-gray-500">Solicitação AGHU:</span> <span class="font-mono">{{ previa.solicitacao_aghu }}</span></p>
            <p>
              <span class="text-gray-500">Exame:</span>
              <strong>{{ previa.tipo_exame || (previa.tipos_exame.length ? previa.tipos_exame.join(' + ') : '—') }}</strong>
              <span v-if="previa.urgente" class="ml-1 rounded bg-red-600 px-1.5 py-0.5 text-[11px] font-bold uppercase text-white">Urgente</span>
            </p>
            <p><span class="text-gray-500">Data:</span> {{ formatarData(previa.data_solicitacao) }}</p>
            <p><span class="text-gray-500">Origem:</span> {{ previa.origem || '—' }}</p>
            <p><span class="text-gray-500">Unidade:</span> {{ previa.unidade || '—' }}</p>
            <p><span class="text-gray-500">Especialidade:</span> {{ previa.especialidade || '—' }}</p>
            <p><span class="text-gray-500">Status no AGHU:</span> {{ previa.status_descricao || previa.status_aghu || '—' }}</p>
            <p><span class="text-gray-500">Paciente:</span> {{ previa.paciente_nome }}</p>
            <p><span class="text-gray-500">Prontuário:</span> <span class="font-mono">{{ previa.prontuario_aghu || '—' }}</span></p>
          </div>

          <div v-if="previa.pendencias.length" class="rounded border border-red-200 bg-red-50 p-3 text-red-800" role="alert">
            <p class="font-semibold">Esta solicitação não pode ser aberta no SAP:</p>
            <ul class="ml-5 list-disc">
              <li v-for="p in previa.pendencias" :key="p">{{ textoPendencia(p) }}</li>
            </ul>
            <p class="mt-1 text-xs">Acione a TI para conferir a solicitação no AGHU.</p>
          </div>
          <p v-else-if="previa.solicitacao_existente" class="rounded bg-amber-50 p-3 text-amber-800">
            Já aberta no SAP como <strong class="font-mono">{{ previa.solicitacao_existente }}</strong>.
          </p>

          <div>
            <p class="mb-1 font-semibold text-gray-700">
              Amostras destinadas à Anatomia ({{ previa.amostras.length }})
              <span v-if="previa.amostras_canceladas" class="font-normal text-gray-500">
                · {{ previa.amostras_canceladas }} cancelada(s) no AGHU, fora da abertura
              </span>
            </p>
            <div class="overflow-x-auto rounded border border-gray-200">
              <table class="w-full text-left">
                <thead>
                  <tr class="bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500">
                    <th class="px-2 py-1">ID</th>
                    <th class="px-2 py-1">Código</th>
                    <th class="px-2 py-1">Exame</th>
                    <th class="px-2 py-1">Descrição do material</th>
                    <th class="px-2 py-1">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-if="!previa.amostras.length"><td colspan="5" class="px-2 py-2 text-center text-gray-500">Nenhuma amostra vigente.</td></tr>
                  <tr v-for="a in previa.amostras" :key="a.id_amostra || String(a.amostra_aghu)">
                    <td class="px-2 py-1 font-mono whitespace-nowrap">{{ a.id_amostra || a.amostra_aghu }}</td>
                    <td class="px-2 py-1 font-mono">{{ a.codigo_exame || '—' }}<span v-if="a.tipo_exame" class="text-gray-500"> ({{ a.tipo_exame }})</span></td>
                    <td class="px-2 py-1">{{ a.nome_exame || '—' }}</td>
                    <td class="px-2 py-1">{{ a.descricao || 'Sem descrição no AGHU' }}</td>
                    <td class="px-2 py-1">{{ a.status_descricao || a.status || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <p class="text-xs text-gray-500">Os dados vêm do AGHU e não podem ser editados no SAP. A abertura fica registrada com seu usuário, data e hora.</p>
        </template>
      </div>
      <template #footer>
        <Button variant="default" @click="fecharModalAghu">Fechar</Button>
        <Button variant="primary" :disabled="!podeAbrir(previa)" :loading="abrindo" @click="confirmarAbertura">Abrir no SAP</Button>
      </template>
    </Modal>

    <!-- Confirmação de retirar / desfazer -->
    <Modal :show="!!confirmacao" @close="confirmacao = null">
      <template #header>{{ confirmacao?.acao === 'retirar' ? 'Marcar como retirado' : 'Desfazer retirada' }}</template>
      <div v-if="confirmacao" class="space-y-2 text-sm">
        <p v-if="confirmacao.acao === 'retirar'">
          Confirma que o material da solicitação <strong class="font-mono">{{ confirmacao.item.identificador_interno }}</strong>
          ({{ confirmacao.item.paciente_nome }}) foi retirado da recepção? Ela seguirá para a próxima fase.
        </p>
        <p v-else>
          Desfazer a retirada da solicitação <strong class="font-mono">{{ confirmacao.item.identificador_interno }}</strong>?
          Ela voltará para "Não retirados".
        </p>
        <p class="text-xs text-gray-500">A ação fica registrada com seu usuário, data e hora.</p>
      </div>
      <template #footer>
        <Button variant="default" @click="confirmacao = null">Cancelar</Button>
        <Button :variant="confirmacao?.acao === 'retirar' ? 'primary' : 'warning'" :loading="processando" @click="confirmar">Confirmar</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import Button from '../components/Button.vue';
import Modal from '../components/Modal.vue';
import { useAuthStore } from '../stores/auth';
import type { PreviaAghu, SituacaoRetirada, SolicitacaoExame } from '../services/solicitacoes';
import {
  TIPOS_EXAME, abrirSolicitacao, consultarSolicitacaoAghu, desfazerRetirada, formatarData, formatarDataHora,
  listarSolicitacoes, marcarRetirado, mensagemErro, podeAbrir, rotuloEtapa, textoPendencia,
} from '../services/solicitacoes';

const ABAS = [
  { rota: '/solicitacoes/nao-retirados', rotulo: 'Não retirados', situacao: 'NAO_RETIRADO' },
  { rota: '/solicitacoes/retirados', rotulo: 'Retirados', situacao: 'RETIRADO' },
  { rota: '/solicitacoes/arquivados', rotulo: 'Arquivados', situacao: 'ARQUIVADO' },
] as const;
const LIMITE = 20;

const route = useRoute();
const auth = useAuthStore();
const situacao = computed(() => String(route.meta.situacao || 'NAO_RETIRADO'));
const ehRecepcao = computed(() => auth.hasRole('RECEPCAO'));
const colunas = computed(() => 7 + (situacao.value === 'RETIRADO' ? 1 : 0) + (ehRecepcao.value ? 1 : 0));
const descricaoAba = computed(() => situacao.value === 'RETIRADO'
  ? 'Solicitações cujo material já saiu da recepção, da retirada mais recente para a mais antiga.'
  : 'Solicitações recebidas cujo material ainda está na recepção. Urgências no topo; depois, do recebimento mais antigo para o mais recente.');

const filtros = reactive({ busca: '', tipo_exame: '', de: '', ate: '' });
const itens = ref<SolicitacaoExame[]>([]);
const total = ref(0);
const pagina = ref(1);
const carregando = ref(false);
const erro = ref('');
const aviso = ref('');
const totalPaginas = computed(() => Math.max(1, Math.ceil(total.value / LIMITE)));

const confirmacao = ref<{ item: SolicitacaoExame; acao: 'retirar' | 'desfazer' } | null>(null);
const processando = ref(false);

/** Carrega a página pedida da aba atual com os filtros. */
async function pesquisar(novaPagina: number): Promise<void> {
  if (situacao.value === 'ARQUIVADO') return;
  carregando.value = true;
  erro.value = '';
  try {
    const dados = await listarSolicitacoes(situacao.value as SituacaoRetirada, filtros, novaPagina, LIMITE);
    itens.value = dados.items;
    total.value = dados.total;
    pagina.value = dados.pagina;
  } catch (e) {
    erro.value = mensagemErro(e, 'Não foi possível carregar as solicitações.');
  } finally {
    carregando.value = false;
  }
}

/** Limpa os filtros e recarrega. */
function limpar(): void {
  Object.assign(filtros, { busca: '', tipo_exame: '', de: '', ate: '' });
  pesquisar(1);
}

/** Abre a confirmação de retirar ou desfazer. */
function pedirConfirmacao(item: SolicitacaoExame, acao: 'retirar' | 'desfazer'): void {
  aviso.value = '';
  erro.value = '';
  confirmacao.value = { item, acao };
}

/** Executa a ação confirmada e recarrega a lista. */
async function confirmar(): Promise<void> {
  if (!confirmacao.value) return;
  const { item, acao } = confirmacao.value;
  processando.value = true;
  try {
    if (acao === 'retirar') {
      await marcarRetirado(item.id);
      aviso.value = `Solicitação ${item.identificador_interno} marcada como retirada.`;
    } else {
      await desfazerRetirada(item.id);
      aviso.value = `Retirada da solicitação ${item.identificador_interno} desfeita.`;
    }
    confirmacao.value = null;
    await pesquisar(pagina.value);
  } catch (e) {
    confirmacao.value = null;
    erro.value = mensagemErro(e);
  } finally {
    processando.value = false;
  }
}

// --- Abrir solicitação do AGHU (Recepção) ---------------------------------
const modalAghu = ref(false);
const numeroAghu = ref('');
const previa = ref<PreviaAghu | null>(null);
const erroAghu = ref('');
const consultando = ref(false);
const abrindo = ref(false);

/** Abre o modal limpo. */
function abrirModalAghu(): void {
  aviso.value = '';
  erro.value = '';
  numeroAghu.value = '';
  previa.value = null;
  erroAghu.value = '';
  modalAghu.value = true;
}

/** Fecha o modal. */
function fecharModalAghu(): void {
  modalAghu.value = false;
}

/** Consulta a solicitação no AGHU (somente leitura) e mostra a prévia. */
async function consultarAghu(): Promise<void> {
  const numero = numeroAghu.value.trim();
  previa.value = null;
  erroAghu.value = '';
  if (!/^\d+$/.test(numero)) {
    erroAghu.value = 'Informe o número da solicitação (só dígitos).';
    return;
  }
  consultando.value = true;
  try {
    previa.value = await consultarSolicitacaoAghu(numero);
  } catch (e) {
    erroAghu.value = mensagemErro(e, 'Não foi possível consultar o AGHU.');
  } finally {
    consultando.value = false;
  }
}

/** Abre a solicitação no SAP e mostra o identificador interno e os IDs das amostras. */
async function confirmarAbertura(): Promise<void> {
  if (!previa.value || !podeAbrir(previa.value)) return;
  abrindo.value = true;
  erroAghu.value = '';
  try {
    const aberta = await abrirSolicitacao(String(previa.value.solicitacao_aghu));
    const ids = aberta.amostras.map((a) => a.identificador || a.amostra_aghu).join(', ');
    aviso.value = `Solicitação ${aberta.identificador_interno} aberta com ${aberta.amostras.length} amostra(s): ${ids}.`;
    modalAghu.value = false;
    await pesquisar(1);
  } catch (e) {
    erroAghu.value = mensagemErro(e, 'Não foi possível abrir a solicitação.');
  } finally {
    abrindo.value = false;
  }
}

watch(situacao, () => {
  aviso.value = '';
  Object.assign(filtros, { busca: '', tipo_exame: '', de: '', ate: '' });
  pesquisar(1);
}, { immediate: true });
</script>
