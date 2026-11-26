<!--
  Solicitações de Exames (MVP): abas "Não retirados", "Retirados" e "Arquivados" (em breve).

  - Não retirados: urgentes no topo; depois do recebimento mais antigo para o mais recente.
  - Retirados: da retirada mais recente para a mais antiga.
  - Só a Recepção marca (ou desfaz) a retirada, sempre com confirmação; o backend registra e audita.
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


      <p class="text-sm text-gray-600">{{ descricaoAba }}</p>

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
          <span class="shrink-0">{{ situacao === 'RETIRADO' ? 'Retirado entre' : situacao === 'ARQUIVADO' ? 'Atualizado entre' : 'Recebido entre' }}</span>
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
              <th class="px-3 py-2">{{ situacao === 'RETIRADO' ? 'Retirado em' : situacao === 'ARQUIVADO' ? 'Arquivado em' : 'Recebido em' }}</th>
              <th v-if="situacao === 'RETIRADO'" class="px-3 py-2">Fase atual</th>
              <th v-if="estacaoAutenticada" class="px-3 py-2"></th>
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
                {{ formatarDataHora(situacao === 'RETIRADO' ? s.retirado_em : situacao === 'ARQUIVADO' ? s.atualizado_em : s.criado_em) }}
                <span v-if="situacao === 'RETIRADO' && s.retirado_por" class="block text-xs text-gray-500">por {{ s.retirado_por }}</span>
              </td>
              <td v-if="situacao === 'RETIRADO'" class="px-3 py-3">{{ rotuloEtapa(s.etapa_atual) }}</td>
              <td v-if="estacaoAutenticada" class="px-3 py-3 text-right">
                <Button v-if="situacao === 'NAO_RETIRADO'" variant="primary" @click="pedirConfirmacao(s, 'retirar')">Confirmar retirada</Button>
                <Button v-else-if="situacao === 'RETIRADO'" variant="default" @click="pedirConfirmacao(s, 'desfazer')">Desfazer</Button>
                <Button v-else variant="default" @click="abrirArquivo(s.id)">Histórico e laudos</Button>
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

    <!-- Confirmação de retirar / desfazer -->
    <Modal :show="!!confirmacao" @close="cancelarConfirmacao">
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
        <label class="block">Login do profissional responsável
          <input v-model.trim="credencial.username" type="text" autocomplete="off" class="mt-1 w-full rounded border px-2 py-1" />
        </label>
        <label class="block">Senha institucional do responsável
          <input v-model="credencial.password" type="password" autocomplete="off" class="mt-1 w-full rounded border px-2 py-1" />
        </label>
        <p class="text-xs text-gray-500">A retirada será atribuída a quem confirmar com a própria credencial, mesmo em estação de outra pessoa. A senha não será armazenada.</p>
      </div>
      <template #footer>
        <Button variant="default" @click="cancelarConfirmacao">Cancelar</Button>
        <Button :variant="confirmacao?.acao === 'retirar' ? 'primary' : 'warning'" :loading="processando" :disabled="!credencial.username || !credencial.password" @click="confirmar">Confirmar</Button>
      </template>
    </Modal>
    <Modal :show="arquivoAberto !== null" @close="arquivoAberto = null">
      <template #header>Histórico e laudos disponíveis</template>
      <p v-if="carregandoArquivo" class="text-sm">Carregando...</p>
      <p v-else-if="!arquivoDados" class="text-sm text-gray-500">Histórico indisponível.</p>
      <div v-else-if="arquivoDados" class="space-y-3 text-sm">
        <p class="text-xs text-gray-500">{{ arquivoDados.aviso }}</p>
        <p>Estado: <strong>{{ arquivoDados.estado }}</strong></p>
        <p v-if="arquivoDados.liberacao">Evento: {{ arquivoDados.liberacao.referencia }} · {{ formatarDataHora(arquivoDados.liberacao.liberado_em) }}</p>
        <div v-for="(doc, i) in arquivoDados.documentos" :key="i" class="rounded border p-2">
          <p class="font-semibold">{{ rotuloEtapa(doc.fase) }} · {{ doc.tipo }}</p>
          <p class="whitespace-pre-wrap">{{ doc.conteudo }}</p>
          <p class="text-xs text-gray-500">Validado por {{ doc.validado_por }} · {{ formatarDataHora(doc.validado_em) }}</p>
        </div>
        <LinhaDoTempo v-if="arquivoAberto" :solicitacao-id="arquivoAberto" />
      </div>
      <template #footer><Button variant="default" @click="arquivoAberto = null">Fechar</Button></template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import Button from '../components/Button.vue';
import Modal from '../components/Modal.vue';
import LinhaDoTempo from '../components/LinhaDoTempo.vue';
import { consultarLaudos, type HistoricoLaudo } from '../services/laudos';
import { useAuthStore } from '../stores/auth';
import type { SituacaoRetirada, SolicitacaoExame } from '../services/solicitacoes';
import {
  TIPOS_EXAME, desfazerRetirada, formatarDataHora, listarSolicitacoes, marcarRetirado, mensagemErro, rotuloEtapa,
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
// A ação pode ser iniciada de qualquer estação autenticada; o backend reautentica o profissional Recepção.
const estacaoAutenticada = computed(() => auth.isAuthenticated);
const colunas = computed(() => 7 + (situacao.value === 'RETIRADO' ? 1 : 0) + (estacaoAutenticada.value ? 1 : 0));
const descricaoAba = computed(() => situacao.value === 'RETIRADO'
  ? 'Solicitações cujo material já saiu da recepção, da retirada mais recente para a mais antiga.'
  : situacao.value === 'ARQUIVADO'
    ? 'Solicitações arquivadas, da mais recente para a mais antiga. O registro oficial do laudo permanece no AGHU.'
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
const credencial = reactive({ username: '', password: '' });
const arquivoAberto = ref<number | null>(null);
const arquivoDados = ref<HistoricoLaudo | null>(null);
const carregandoArquivo = ref(false);
function cancelarConfirmacao(): void {
  confirmacao.value = null;
  credencial.username = '';
  credencial.password = '';
}
async function abrirArquivo(id: number): Promise<void> {
  arquivoAberto.value = id;
  arquivoDados.value = null;
  carregandoArquivo.value = true;
  try { arquivoDados.value = await consultarLaudos(id); }
  catch (e) { erro.value = mensagemErro(e); arquivoAberto.value = null; }
  finally { carregandoArquivo.value = false; }
}

/** Carrega a página pedida da aba atual com os filtros. */
async function pesquisar(novaPagina: number): Promise<void> {
  // A aba Arquivados usa os mesmos filtros e paginação das demais.
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
  credencial.username = '';
  credencial.password = '';
  confirmacao.value = { item, acao };
}

/** Executa a ação confirmada e recarrega a lista. */
async function confirmar(): Promise<void> {
  if (!confirmacao.value) return;
  const { item, acao } = confirmacao.value;
  processando.value = true;
  try {
    if (acao === 'retirar') {
      await marcarRetirado(item.id, { ...credencial });
      aviso.value = `Solicitação ${item.identificador_interno} marcada como retirada.`;
    } else {
      await desfazerRetirada(item.id, { ...credencial });
      aviso.value = `Retirada da solicitação ${item.identificador_interno} desfeita.`;
    }
    cancelarConfirmacao();
    await pesquisar(pagina.value);
  } catch (e) {
    cancelarConfirmacao();
    erro.value = mensagemErro(e);
  } finally {
    processando.value = false;
  }
}

watch(situacao, () => {
  aviso.value = '';
  Object.assign(filtros, { busca: '', tipo_exame: '', de: '', ate: '' });
  pesquisar(1);
}, { immediate: true });
</script>
