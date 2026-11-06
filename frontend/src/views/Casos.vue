<!--
  View do fluxo principal do SAP: ciclo de vida do Caso (UC002, UC019, UC017, UC012, UC018).

  ATENÇÃO - contratos assumidos dos componentes base (ajustar se o código real divergir):
    DataTable : props `columns` [{ key, label }], `data` (linhas), `loading`;
                slot de célula `#cell-<key>="{ row }"`.
    Modal     : `v-model` (boolean), prop `title`, slot padrão e slot `#footer`.
    Button    : props `variant` ('primary' | 'secondary' | 'danger'), `loading`, `disabled`; evento `@click`.
-->
<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Casos</h1>
        <p class="text-sm text-gray-500">Abertura, acompanhamento e movimentação dos casos de anatomia patológica.</p>
      </div>
      <Button v-if="podeAbrir" variant="primary" @click="abrirModalNovo">Abrir caso</Button>
    </div>

    <!-- Filtros (RF027) -->
    <div class="grid grid-cols-1 gap-3 rounded-lg border border-gray-200 bg-white p-4 md:grid-cols-6">
      <input v-model="filtros.solicitacao" class="rounded border p-2 text-sm" placeholder="Nº da solicitação" @keyup.enter="pesquisar" />
      <input v-model="filtros.paciente" class="rounded border p-2 text-sm md:col-span-2" placeholder="Paciente" @keyup.enter="pesquisar" />
      <input v-model="filtros.identificador" class="rounded border p-2 text-sm" placeholder="Identificador interno" @keyup.enter="pesquisar" />
      <select v-model="filtros.tipo_exame" class="rounded border p-2 text-sm">
        <option value="">Tipo de exame</option>
        <option v-for="t in TIPOS_EXAME" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filtros.etapa" class="rounded border p-2 text-sm">
        <option value="">Etapa</option>
        <option v-for="(rotulo, chave) in ETAPAS" :key="chave" :value="chave">{{ rotulo }}</option>
      </select>
      <select v-model="filtros.status" class="rounded border p-2 text-sm">
        <option value="">Status</option>
        <option value="EM_ANDAMENTO">Em andamento</option>
        <option value="ARQUIVADO">Arquivado</option>
      </select>
      <div class="flex gap-2 md:col-span-5">
        <Button variant="primary" :loading="store.loading" @click="pesquisar">Buscar</Button>
        <Button variant="secondary" @click="limparFiltros">Limpar</Button>
      </div>
    </div>

    <p v-if="erroLista" class="rounded bg-red-50 p-3 text-sm text-red-700" role="alert">{{ erroLista }}</p>

    <!-- Lista -->
    <DataTable :columns="colunas" :data="store.casos" :loading="store.loading">
      <template #cell-etapa_atual="{ row }">{{ rotuloEtapa(row.etapa_atual) }}</template>
      <template #cell-status="{ row }">
        <span :class="row.status === 'ARQUIVADO' ? 'bg-gray-100 text-gray-700' : 'bg-blue-50 text-blue-700'"
              class="rounded px-2 py-0.5 text-xs font-medium">
          {{ row.status === 'ARQUIVADO' ? 'Arquivado' : 'Em andamento' }}
        </span>
      </template>
      <template #cell-criado_em="{ row }">{{ formatarData(row.criado_em) }}</template>
      <template #cell-acoes="{ row }">
        <Button variant="secondary" @click="abrirModalCaso(row.id)">Abrir</Button>
      </template>
    </DataTable>

    <p v-if="!store.loading && !store.casos.length && buscou" class="text-sm text-gray-500">Nenhum caso encontrado para os filtros informados.</p>

    <div class="flex items-center justify-between text-sm text-gray-600">
      <span>{{ store.total }} caso(s) · página {{ pagina }} de {{ totalPaginas }}</span>
      <div class="flex gap-2">
        <Button variant="secondary" :disabled="pagina <= 1 || store.loading" @click="irParaPagina(pagina - 1)">Anterior</Button>
        <Button variant="secondary" :disabled="pagina >= totalPaginas || store.loading" @click="irParaPagina(pagina + 1)">Próxima</Button>
      </div>
    </div>

    <!-- Modal: abrir caso (UC002) -->
    <Modal v-model="modalNovo" title="Abrir caso a partir do AGHU">
      <div class="space-y-4">
        <div class="flex gap-2">
          <input v-model="novo.solicitacao" class="flex-1 rounded border p-2 text-sm" inputmode="numeric" placeholder="Nº da solicitação no AGHU" @keyup.enter="consultarAghu" />
          <select v-model="novo.tipo" class="rounded border p-2 text-sm">
            <option v-for="t in TIPOS_EXAME" :key="t" :value="t">{{ t }}</option>
          </select>
          <Button variant="secondary" :loading="novo.consultando" @click="consultarAghu">Consultar AGHU</Button>
        </div>

        <div v-if="novo.dados" class="space-y-2 rounded border border-gray-200 bg-gray-50 p-3 text-sm">
          <p class="text-xs uppercase text-gray-500">Dados do AGHU (somente leitura)</p>
          <p><strong>Paciente:</strong> {{ novo.dados.paciente_nome }}</p>
          <p v-if="novo.dados.prontuario_aghu"><strong>Prontuário:</strong> {{ novo.dados.prontuario_aghu }}</p>
          <p><strong>Amostras:</strong> {{ novo.dados.amostras.map(a => a.descricao || `#${a.amostra_aghu}`).join(', ') || '—' }}</p>
          <p v-if="novo.dados.caso_existente" class="text-amber-700">Já existe o caso {{ novo.dados.caso_existente }} para esta solicitação.</p>
        </div>

        <p v-if="novo.erro" class="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">{{ novo.erro }}</p>
      </div>
      <template #footer>
        <Button variant="secondary" @click="modalNovo = false">Cancelar</Button>
        <Button variant="primary" :loading="novo.salvando" :disabled="!novo.dados || !!novo.dados.caso_existente" @click="confirmarAbertura">
          Confirmar e abrir caso
        </Button>
      </template>
    </Modal>

    <!-- Modal: caso (detalhe, ações e histórico) -->
    <Modal v-model="modalCaso" :title="caso ? `Caso ${caso.identificador_interno}` : 'Caso'">
      <div v-if="caso" class="space-y-4 text-sm">
        <div class="grid grid-cols-2 gap-2">
          <p><strong>Paciente:</strong> {{ caso.paciente_nome }}</p>
          <p><strong>Solicitação:</strong> {{ caso.solicitacao_aghu }}</p>
          <p><strong>Exame:</strong> {{ caso.tipo_exame }}</p>
          <p><strong>Etapa atual:</strong> {{ rotuloEtapa(caso.etapa_atual) }}</p>
        </div>
        <p><strong>Amostras:</strong> {{ caso.amostras.map(a => a.descricao || `#${a.amostra_aghu}`).join(', ') }}</p>

        <p v-if="erroCaso" class="rounded bg-red-50 p-2 text-red-700" role="alert">{{ erroCaso }}</p>

        <!-- Ações permitidas ao perfil e ao fluxo configurado -->
        <div v-if="modo === 'detalhe'" class="flex flex-wrap gap-2">
          <Button v-if="caso.acoes.pode_concluir" variant="primary" :loading="processando" @click="concluirEtapa">Concluir etapa</Button>
          <Button v-if="caso.acoes.destinos_encaminhamento.length" variant="secondary" @click="iniciarAcao('encaminhar')">Encaminhar</Button>
          <Button v-if="caso.acoes.pode_retornar" variant="secondary" @click="iniciarAcao('retornar')">Retornar à origem</Button>
          <span v-if="!caso.acoes.pode_concluir && !caso.acoes.pode_retornar && !caso.acoes.destinos_encaminhamento.length" class="text-gray-500">
            Nenhuma ação disponível para o seu perfil nesta etapa.
          </span>
        </div>

        <div v-else class="space-y-2 rounded border border-gray-200 p-3">
          <select v-if="modo === 'encaminhar'" v-model="acao.destino" class="w-full rounded border p-2">
            <option value="">Selecione o destino</option>
            <option v-for="d in caso.acoes.destinos_encaminhamento" :key="d" :value="d">{{ rotuloEtapa(d) }}</option>
          </select>
          <textarea v-model="acao.motivo" rows="3" maxlength="500" class="w-full rounded border p-2" placeholder="Motivo (obrigatório)"></textarea>
          <div class="flex gap-2">
            <Button variant="primary" :loading="processando" :disabled="!acao.motivo.trim() || (modo === 'encaminhar' && !acao.destino)" @click="confirmarAcao">Confirmar</Button>
            <Button variant="secondary" @click="modo = 'detalhe'">Cancelar</Button>
          </div>
        </div>

        <!-- Histórico (UC018) -->
        <div>
          <h3 class="mb-2 font-semibold">Histórico</h3>
          <ol class="space-y-2 border-l-2 border-gray-200 pl-3">
            <li v-for="m in historico" :key="m.id">
              <p class="font-medium">{{ rotuloMovimento(m) }}</p>
              <p class="text-xs text-gray-500">{{ formatarData(m.criado_em) }} · {{ m.usuario }}</p>
              <p v-if="m.motivo" class="text-xs text-gray-600">Motivo: {{ m.motivo }}</p>
            </li>
          </ol>
        </div>
      </div>
      <template #footer>
        <Button variant="secondary" @click="modalCaso = false">Fechar</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import Button from '../components/Button.vue';
import DataTable from '../components/DataTable.vue';
import Modal from '../components/Modal.vue';
import {
  mensagemErro, useCasoStore,
  type CasoDetalhe, type FiltrosCaso, type Movimentacao, type SolicitacaoAghu,
} from '../stores/caso';
// TODO: trocar por `useAuthStore().user?.perfil` (nome do campo conforme stores/auth.ts).
import { useAuthStore } from '../stores/auth';

const TIPOS_EXAME = ['HP', 'CO', 'CG', 'CCV'];
const ETAPAS: Record<string, string> = {
  RECEPCAO: 'Recepção', MACROSCOPIA: 'Macroscopia', CONGELACAO: 'Congelação',
  PROCESSAMENTO: 'Processamento técnico', IHQ: 'Imunohistoquímico',
  MICROSCOPIA: 'Microscopia', REDE_EXTERNA: 'Rede externa', ARQUIVO: 'Arquivo',
};
const LIMITE = 20;

const store = useCasoStore();
const auth = useAuthStore() as any;
const podeAbrir = computed(() => String(auth.user?.perfil ?? '').toUpperCase() === 'RECEPCAO');

const colunas = [
  { key: 'identificador_interno', label: 'Identificador' },
  { key: 'solicitacao_aghu', label: 'Solicitação' },
  { key: 'paciente_nome', label: 'Paciente' },
  { key: 'tipo_exame', label: 'Exame' },
  { key: 'etapa_atual', label: 'Etapa' },
  { key: 'status', label: 'Status' },
  { key: 'criado_em', label: 'Aberto em' },
  { key: 'acoes', label: '' },
];

// --- Lista ------------------------------------------------------------------
const filtros = reactive<FiltrosCaso>({ solicitacao: '', paciente: '', identificador: '', tipo_exame: '', etapa: '', status: '' });
const pagina = ref(1);
const buscou = ref(false);
const erroLista = ref('');
const totalPaginas = computed(() => Math.max(1, Math.ceil(store.total / LIMITE)));

async function carregar() {
  erroLista.value = '';
  try {
    await store.buscar(filtros, pagina.value, LIMITE);
  } catch (e) {
    erroLista.value = mensagemErro(e, 'Não foi possível carregar os casos.');
  } finally {
    buscou.value = true;
  }
}
const pesquisar = () => { pagina.value = 1; return carregar(); };
const irParaPagina = (n: number) => { pagina.value = n; return carregar(); };
function limparFiltros() {
  Object.assign(filtros, { solicitacao: '', paciente: '', identificador: '', tipo_exame: '', etapa: '', status: '' });
  return pesquisar();
}

// --- Abrir caso (UC002) -----------------------------------------------------
const modalNovo = ref(false);
const novo = reactive({
  solicitacao: '', tipo: 'HP', consultando: false, salvando: false, erro: '',
  dados: null as SolicitacaoAghu | null,
});

function abrirModalNovo() {
  Object.assign(novo, { solicitacao: '', tipo: 'HP', consultando: false, salvando: false, erro: '', dados: null });
  modalNovo.value = true;
}
async function consultarAghu() {
  novo.erro = ''; novo.dados = null; novo.consultando = true;
  try {
    novo.dados = await store.consultarAghu(novo.solicitacao.trim());
  } catch (e) {
    novo.erro = mensagemErro(e);
  } finally {
    novo.consultando = false;
  }
}
async function confirmarAbertura() {
  novo.erro = ''; novo.salvando = true;
  try {
    const criado = await store.abrir(novo.solicitacao.trim(), novo.tipo);
    modalNovo.value = false;
    await pesquisar();
    await abrirModalCaso(criado.id);
  } catch (e) {
    novo.erro = mensagemErro(e);
  } finally {
    novo.salvando = false;
  }
}

// --- Caso: detalhe, ações e histórico (UC017, UC012, UC018) ------------------
const modalCaso = ref(false);
const caso = ref<CasoDetalhe | null>(null);
const historico = ref<Movimentacao[]>([]);
const erroCaso = ref('');
const processando = ref(false);
const modo = ref<'detalhe' | 'encaminhar' | 'retornar'>('detalhe');
const acao = reactive({ destino: '', motivo: '' });

async function recarregarCaso(id: number) {
  [caso.value, historico.value] = await Promise.all([store.obter(id), store.historico(id)]);
}
async function abrirModalCaso(id: number) {
  erroCaso.value = ''; modo.value = 'detalhe'; caso.value = null; historico.value = [];
  modalCaso.value = true;
  try {
    await recarregarCaso(id);
  } catch (e) {
    erroCaso.value = mensagemErro(e);
  }
}
function iniciarAcao(tipo: 'encaminhar' | 'retornar') {
  acao.destino = ''; acao.motivo = ''; erroCaso.value = ''; modo.value = tipo;
}
async function executar(fn: () => Promise<CasoDetalhe>) {
  if (!caso.value) return;
  erroCaso.value = ''; processando.value = true;
  try {
    const id = caso.value.id;
    await fn();
    modo.value = 'detalhe';
    await Promise.all([recarregarCaso(id), carregar()]);
  } catch (e) {
    erroCaso.value = mensagemErro(e);
  } finally {
    processando.value = false;
  }
}
const concluirEtapa = () => executar(() => store.concluirEtapa(caso.value!.id));
const confirmarAcao = () =>
  executar(() =>
    modo.value === 'encaminhar'
      ? store.encaminhar(caso.value!.id, acao.destino, acao.motivo.trim())
      : store.retornar(caso.value!.id, acao.motivo.trim()),
  );

// --- Formatação ---------------------------------------------------------------
const rotuloEtapa = (e?: string | null) => (e ? ETAPAS[e] ?? e : '—');
const formatarData = (iso: string) => (iso ? new Date(iso).toLocaleString('pt-BR') : '—');
function rotuloMovimento(m: Movimentacao): string {
  const origem = rotuloEtapa(m.etapa_origem);
  const destino = rotuloEtapa(m.etapa_destino);
  switch (m.tipo) {
    case 'ABERTURA': return `Caso aberto em ${destino}`;
    case 'CONCLUSAO': return `${origem} concluída → ${destino}`;
    case 'ENCAMINHAMENTO': return `Encaminhado: ${origem} → ${destino}`;
    case 'RETORNO': return `Retornado: ${origem} → ${destino}`;
    default: return m.tipo;
  }
}

onMounted(carregar);
</script>