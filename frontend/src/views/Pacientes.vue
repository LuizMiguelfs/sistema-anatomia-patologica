<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-bold">Pacientes</h1>
        <p class="text-sm text-gray-500 mt-1">
          Fonte de dados:
          <span
            class="ml-1 px-2 py-0.5 rounded text-xs font-bold"
            :class="capacidades.escrita ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'"
          >
            {{ rotuloFonte }}
          </span>
        </p>
      </div>
      <Button v-if="capacidades.escrita" variant="primary" @click="abrirCadastro">
        <template #icon><PlusIcon class="h-5 w-5" /></template>
        Novo paciente
      </Button>
    </div>

    <!-- Busca -->
    <Card class="mb-6">
      <form class="flex flex-wrap items-end gap-3" @submit.prevent="buscarAgora">
        <div class="flex-1 min-w-64">
          <label for="termoBusca" class="form-label">Buscar paciente</label>
          <div class="relative">
            <span class="form-control-icon"><MagnifyingGlassIcon class="h-5 w-5 text-gray-400" /></span>
            <input
              id="termoBusca"
              v-model="termo"
              type="search"
              maxlength="100"
              placeholder="Nome (mín. 3 letras), código, CPF ou CNS"
              class="form-control pl-10"
            />
          </div>
          <p v-if="avisoBusca" class="text-xs text-yellow-700 mt-1">{{ avisoBusca }}</p>
        </div>
        <Button type="submit" variant="success" :loading="carregando">Buscar</Button>
        <Button type="button" variant="default" :disabled="!termo" @click="limparBusca">Limpar</Button>
      </form>
    </Card>

    <!-- Listagem -->
    <Card>
      <div v-if="carregando" class="text-center text-sm text-gray-500 py-2">Carregando...</div>
      <DataTable :headers="headers" :items="linhas">
        <template #actions="{ item }">
          <div class="flex space-x-2">
            <Button variant="info" class="!py-1 !px-2" title="Visualizar" @click="visualizar(item.codigo)">
              <EyeIcon class="h-4 w-4" />
            </Button>
            <Button v-if="capacidades.escrita" variant="warning" class="!py-1 !px-2" title="Editar" @click="abrirEdicao(item.codigo)">
              <PencilSquareIcon class="h-4 w-4" />
            </Button>
            <Button v-if="capacidades.exclusao" variant="danger" class="!py-1 !px-2" title="Excluir" @click="pedirExclusao(item.codigo)">
              <TrashIcon class="h-4 w-4" />
            </Button>
          </div>
        </template>
      </DataTable>

      <div class="flex items-center justify-between mt-4 text-sm text-gray-600">
        <span>Página {{ pagina + 1 }} · {{ pacientes.length }} registro(s)</span>
        <div class="flex space-x-2">
          <Button variant="default" class="!py-1" :disabled="pagina === 0 || carregando" @click="mudarPagina(-1)">Anterior</Button>
          <Button variant="default" class="!py-1" :disabled="!temProxima || carregando" @click="mudarPagina(1)">Próxima</Button>
        </div>
      </div>
    </Card>

    <!-- Modal: detalhes -->
    <Modal :show="!!detalhe" @close="detalhe = null">
      <template #header>Detalhes do paciente</template>
      <dl v-if="detalhe" class="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div><dt class="font-medium text-gray-500">Código</dt><dd>{{ detalhe.codigo }}</dd></div>
        <div><dt class="font-medium text-gray-500">Nascimento</dt><dd>{{ formatarData(detalhe.dt_nascimento) }}</dd></div>
        <div class="col-span-2"><dt class="font-medium text-gray-500">Nome</dt><dd>{{ detalhe.nome }}</dd></div>
        <div><dt class="font-medium text-gray-500">Sexo</dt><dd>{{ rotuloSexo(detalhe.sexo) }}</dd></div>
        <div><dt class="font-medium text-gray-500">Raça/Cor</dt><dd>{{ rotuloCor(detalhe.cor) }}</dd></div>
        <div><dt class="font-medium text-gray-500">CPF</dt><dd>{{ detalhe.cpf || '—' }}</dd></div>
        <div><dt class="font-medium text-gray-500">CNS</dt><dd>{{ detalhe.cns || '—' }}</dd></div>
        <div class="col-span-2"><dt class="font-medium text-gray-500">Nome da mãe</dt><dd>{{ detalhe.nome_mae || '—' }}</dd></div>
        <div class="col-span-2"><dt class="font-medium text-gray-500">Nome do pai</dt><dd>{{ detalhe.nome_pai || '—' }}</dd></div>
      </dl>
      <template #footer>
        <Button v-if="capacidades.escrita && detalhe" variant="warning" @click="abrirEdicao(detalhe.codigo)">Editar</Button>
        <Button variant="default" @click="detalhe = null">Fechar</Button>
      </template>
    </Modal>

    <!-- Modal: cadastro / edição -->
    <Modal :show="formAberto" @close="fecharFormulario">
      <template #header>{{ codigoEmEdicao ? `Editar paciente #${codigoEmEdicao}` : 'Novo paciente' }}</template>
      <form id="formPaciente" class="grid grid-cols-2 gap-x-4" novalidate @submit.prevent="salvar">
        <div class="form-group col-span-2">
          <label for="nome" class="form-label">Nome completo *</label>
          <input id="nome" v-model="form.nome" maxlength="100" class="form-control" :class="classeErro('nome')" />
          <p v-if="erros.nome" class="text-xs text-red-600 mt-1">{{ erros.nome }}</p>
        </div>
        <div class="form-group">
          <label for="dt_nascimento" class="form-label">Data de nascimento *</label>
          <input id="dt_nascimento" v-model="form.dt_nascimento" type="date" :max="hoje" min="1900-01-01" class="form-control" :class="classeErro('dt_nascimento')" />
          <p v-if="erros.dt_nascimento" class="text-xs text-red-600 mt-1">{{ erros.dt_nascimento }}</p>
        </div>
        <div class="form-group">
          <label for="sexo" class="form-label">Sexo *</label>
          <select id="sexo" v-model="form.sexo" class="form-control" :class="classeErro('sexo')">
            <option value="" disabled>Selecione...</option>
            <option v-for="op in opcoesSexo" :key="op.valor" :value="op.valor">{{ op.rotulo }}</option>
          </select>
          <p v-if="erros.sexo" class="text-xs text-red-600 mt-1">{{ erros.sexo }}</p>
        </div>
        <div class="form-group">
          <label for="cpf" class="form-label">CPF</label>
          <input id="cpf" :value="form.cpf" inputmode="numeric" maxlength="14" placeholder="000.000.000-00" class="form-control" :class="classeErro('cpf')" @input="aoDigitarCpf" />
          <p v-if="erros.cpf" class="text-xs text-red-600 mt-1">{{ erros.cpf }}</p>
        </div>
        <div class="form-group">
          <label for="cns" class="form-label">CNS</label>
          <input id="cns" v-model="form.cns" inputmode="numeric" maxlength="15" placeholder="15 dígitos" class="form-control" :class="classeErro('cns')" />
          <p v-if="erros.cns" class="text-xs text-red-600 mt-1">{{ erros.cns }}</p>
        </div>
        <div class="form-group col-span-2">
          <label for="cor" class="form-label">Raça/Cor</label>
          <select id="cor" v-model="form.cor" class="form-control">
            <option value="">Não informada</option>
            <option v-for="op in opcoesCor" :key="op.valor" :value="op.valor">{{ op.rotulo }}</option>
          </select>
        </div>
        <div class="form-group col-span-2">
          <label for="nome_mae" class="form-label">Nome da mãe</label>
          <input id="nome_mae" v-model="form.nome_mae" maxlength="100" class="form-control" />
        </div>
        <div class="form-group col-span-2 !mb-0">
          <label for="nome_pai" class="form-label">Nome do pai</label>
          <input id="nome_pai" v-model="form.nome_pai" maxlength="100" class="form-control" />
        </div>
      </form>
      <p v-if="erroServidor" class="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">{{ erroServidor }}</p>
      <template #footer>
        <Button variant="default" :disabled="salvando" @click="fecharFormulario">Cancelar</Button>
        <Button type="submit" form="formPaciente" variant="primary" :loading="salvando">Salvar</Button>
      </template>
    </Modal>

    <!-- Modal: confirmação de exclusão -->
    <Modal :show="!!pacienteAExcluir" @close="pacienteAExcluir = null">
      <template #header>Excluir paciente</template>
      <p v-if="pacienteAExcluir">
        Confirma a exclusão de <strong>{{ pacienteAExcluir.nome }}</strong> (código {{ pacienteAExcluir.codigo }})?
      </p>
      <p class="text-xs text-gray-500 mt-2">
        A exclusão é lógica: o registro deixa de aparecer, mas é preservado e a ação fica registrada na auditoria.
      </p>
      <template #footer>
        <Button variant="default" :disabled="excluindo" @click="pacienteAExcluir = null">Cancelar</Button>
        <Button variant="danger" :loading="excluindo" @click="confirmarExclusao">Excluir</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import { EyeIcon, MagnifyingGlassIcon, PencilSquareIcon, PlusIcon, TrashIcon } from '@heroicons/vue/24/outline';
import api from '../services/api';
import Card from '../components/Card.vue';
import DataTable from '../components/DataTable.vue';
import Button from '../components/Button.vue';
import Modal from '../components/Modal.vue';

interface Paciente {
  codigo: number;
  nome: string;
  dt_nascimento: string | null;
  sexo: string | null;
  cor: string | null;
  nome_mae: string | null;
  nome_pai: string | null;
  cpf: string | null;
  cns: string | null;
}

interface Capacidades {
  fonte: string;
  escrita: boolean;
  exclusao: boolean;
}

interface FormPaciente {
  nome: string;
  dt_nascimento: string;
  sexo: string;
  cor: string;
  cpf: string;
  cns: string;
  nome_mae: string;
  nome_pai: string;
}

const TAMANHO_PAGINA = 20;
const MIN_CARACTERES_NOME = 3;
const TERMO_NUMERICO = /^\d[\d.\-\s]*$/;

const opcoesSexo = [
  { valor: 'F', rotulo: 'Feminino' },
  { valor: 'M', rotulo: 'Masculino' },
  { valor: 'I', rotulo: 'Ignorado' },
];
const opcoesCor = [
  { valor: 'BRANCA', rotulo: 'Branca' },
  { valor: 'PRETA', rotulo: 'Preta' },
  { valor: 'PARDA', rotulo: 'Parda' },
  { valor: 'AMARELA', rotulo: 'Amarela' },
  { valor: 'INDIGENA', rotulo: 'Indígena' },
  { valor: 'SEM_INFORMACAO', rotulo: 'Sem informação' },
];

const toast = useToast();

// ---------------------------------------------------------------- estado
const capacidades = ref<Capacidades>({ fonte: '', escrita: false, exclusao: false });
const pacientes = ref<Paciente[]>([]);
const carregando = ref(false);
const termo = ref('');
const pagina = ref(0);
const temProxima = ref(false);
let requisicaoAtual = 0;
let timerBusca: ReturnType<typeof setTimeout> | undefined;

const detalhe = ref<Paciente | null>(null);
const pacienteAExcluir = ref<Paciente | null>(null);
const excluindo = ref(false);

const formAberto = ref(false);
const codigoEmEdicao = ref<number | null>(null);
const salvando = ref(false);
const erroServidor = ref('');
const form = reactive<FormPaciente>(formVazio());
const erros = reactive<Record<string, string>>({});

const hoje = new Date().toISOString().slice(0, 10);

const headers = [
  { text: 'Código', value: 'codigo' },
  { text: 'Nome', value: 'nome' },
  { text: 'Nascimento', value: 'nascimento' },
  { text: 'Sexo', value: 'sexo' },
  { text: 'CPF', value: 'cpf' },
  { text: 'Nome da mãe', value: 'nome_mae' },
];

const linhas = computed(() =>
  pacientes.value.map((p) => ({
    id: p.codigo,
    codigo: p.codigo,
    nome: p.nome,
    nascimento: formatarData(p.dt_nascimento),
    sexo: p.sexo || '—',
    cpf: p.cpf || '—',
    nome_mae: p.nome_mae || '—',
  })),
);

const rotuloFonte = computed(() => {
  if (!capacidades.value.fonte) return '...';
  if (capacidades.value.fonte === 'POSTGRES') {
    return capacidades.value.escrita ? 'AGHU (escrita habilitada)' : 'AGHU (somente leitura)';
  }
  return capacidades.value.fonte;
});

const termoNormalizado = computed(() => termo.value.trim());
const avisoBusca = computed(() => {
  const t = termoNormalizado.value;
  if (t && !TERMO_NUMERICO.test(t) && t.length < MIN_CARACTERES_NOME) {
    return `Digite ao menos ${MIN_CARACTERES_NOME} letras para buscar por nome.`;
  }
  return '';
});

// ------------------------------------------------------------- utilitários
function formVazio(): FormPaciente {
  return { nome: '', dt_nascimento: '', sexo: '', cor: '', cpf: '', cns: '', nome_mae: '', nome_pai: '' };
}

function mensagemErro(error: any, padrao: string): string {
  const detail = error?.response?.data?.detail;
  return typeof detail === 'string' ? detail : padrao;
}

function formatarData(iso: string | null): string {
  if (!iso) return '—';
  const [ano, mes, dia] = iso.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}

function rotuloSexo(valor: string | null): string {
  return opcoesSexo.find((o) => o.valor === valor)?.rotulo || valor || '—';
}

function rotuloCor(valor: string | null): string {
  return opcoesCor.find((o) => o.valor === valor)?.rotulo || valor || '—';
}

function somenteDigitos(valor: string): string {
  return valor.replace(/\D/g, '');
}

function mascararCpf(valor: string): string {
  const d = somenteDigitos(valor).slice(0, 11);
  return d
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1-$2');
}

function cpfValido(cpf: string): boolean {
  const d = somenteDigitos(cpf);
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  for (const pos of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < pos; i++) soma += Number(d[i]) * (pos + 1 - i);
    if (((soma * 10) % 11) % 10 !== Number(d[pos])) return false;
  }
  return true;
}

function classeErro(campo: string): string {
  return erros[campo] ? 'border-red-500' : '';
}

// ---------------------------------------------------------------- listagem
async function carregarCapacidades() {
  try {
    const { data } = await api.get<Capacidades>('/api/pacientes/capacidades');
    capacidades.value = data;
  } catch (error) {
    toast.error(mensagemErro(error, 'Falha ao consultar a fonte de dados de pacientes.'));
  }
}

async function carregarPacientes() {
  if (avisoBusca.value) return;
  const id = ++requisicaoAtual;
  carregando.value = true;
  try {
    const params: Record<string, string | number> = {
      limite: TAMANHO_PAGINA + 1, // 1 a mais para saber se existe próxima página
      offset: pagina.value * TAMANHO_PAGINA,
    };
    if (termoNormalizado.value) params.termo = termoNormalizado.value;
    const { data } = await api.get<Paciente[]>('/api/pacientes', { params });
    if (id !== requisicaoAtual) return; // resposta antiga: descarta
    temProxima.value = data.length > TAMANHO_PAGINA;
    pacientes.value = data.slice(0, TAMANHO_PAGINA);
  } catch (error) {
    if (id === requisicaoAtual) toast.error(mensagemErro(error, 'Falha ao carregar a lista de pacientes.'));
  } finally {
    if (id === requisicaoAtual) carregando.value = false;
  }
}

function buscarAgora() {
  clearTimeout(timerBusca);
  pagina.value = 0;
  carregarPacientes();
}

function limparBusca() {
  termo.value = '';
  buscarAgora();
}

function mudarPagina(delta: number) {
  pagina.value = Math.max(0, pagina.value + delta);
  carregarPacientes();
}

// Ao editar um campo, remove a mensagem de erro dele (as demais continuam visíveis).
watch(
  () => ({ ...form }),
  (novo, antigo) => {
    (Object.keys(novo) as (keyof FormPaciente)[]).forEach((campo) => {
      if (novo[campo] !== antigo[campo]) delete erros[campo];
    });
  },
);

watch(termo, () => {
  clearTimeout(timerBusca);
  timerBusca = setTimeout(buscarAgora, 400);
});

async function obterPaciente(codigo: number): Promise<Paciente | null> {
  try {
    const { data } = await api.get<Paciente>(`/api/pacientes/${codigo}`);
    return data;
  } catch (error) {
    toast.error(mensagemErro(error, 'Paciente não encontrado.'));
    return null;
  }
}

async function visualizar(codigo: number) {
  detalhe.value = await obterPaciente(codigo);
}

// ------------------------------------------------------- cadastro / edição
function limparErros() {
  Object.keys(erros).forEach((k) => delete erros[k]);
  erroServidor.value = '';
}

function abrirCadastro() {
  limparErros();
  Object.assign(form, formVazio());
  codigoEmEdicao.value = null;
  formAberto.value = true;
}

async function abrirEdicao(codigo: number) {
  const paciente = await obterPaciente(codigo);
  if (!paciente) return;
  limparErros();
  Object.assign(form, {
    nome: paciente.nome,
    dt_nascimento: paciente.dt_nascimento?.slice(0, 10) || '',
    sexo: paciente.sexo || '',
    cor: opcoesCor.some((o) => o.valor === paciente.cor) ? paciente.cor : '',
    cpf: paciente.cpf ? mascararCpf(paciente.cpf) : '',
    cns: paciente.cns || '',
    nome_mae: paciente.nome_mae || '',
    nome_pai: paciente.nome_pai || '',
  });
  codigoEmEdicao.value = codigo;
  detalhe.value = null;
  formAberto.value = true;
}

function fecharFormulario() {
  if (salvando.value) return;
  formAberto.value = false;
}

function aoDigitarCpf(evento: Event) {
  const alvo = evento.target as HTMLInputElement;
  form.cpf = mascararCpf(alvo.value);
  alvo.value = form.cpf;
}

function validarFormulario(): boolean {
  limparErros();
  const nome = form.nome.trim();
  if (nome.length < 3) erros.nome = 'Informe o nome completo (mín. 3 caracteres).';
  if (!form.dt_nascimento) erros.dt_nascimento = 'Informe a data de nascimento.';
  else if (form.dt_nascimento > hoje) erros.dt_nascimento = 'A data não pode estar no futuro.';
  else if (form.dt_nascimento < '1900-01-01') erros.dt_nascimento = 'Data anterior a 1900.';
  if (!form.sexo) erros.sexo = 'Selecione o sexo.';
  if (form.cpf && !cpfValido(form.cpf)) erros.cpf = 'CPF inválido.';
  const cns = somenteDigitos(form.cns);
  if (form.cns && cns.length !== 15) erros.cns = 'O CNS deve ter 15 dígitos.';
  return Object.keys(erros).length === 0;
}

async function salvar() {
  if (!validarFormulario()) return;
  salvando.value = true;
  const payload = {
    nome: form.nome.trim(),
    dt_nascimento: form.dt_nascimento,
    sexo: form.sexo,
    cor: form.cor || null,
    cpf: form.cpf || null,
    cns: somenteDigitos(form.cns) || null,
    nome_mae: form.nome_mae.trim() || null,
    nome_pai: form.nome_pai.trim() || null,
  };
  try {
    if (codigoEmEdicao.value) {
      const { data } = await api.put<Paciente>(`/api/pacientes/${codigoEmEdicao.value}`, payload);
      toast.success(`Paciente ${data.nome} atualizado.`);
    } else {
      const { data } = await api.post<Paciente>('/api/pacientes', payload);
      toast.success(`Paciente ${data.nome} cadastrado (código ${data.codigo}).`);
    }
    salvando.value = false;
    formAberto.value = false;
    await carregarPacientes();
  } catch (error) {
    erroServidor.value = mensagemErro(error, 'Não foi possível salvar o paciente.');
  } finally {
    salvando.value = false;
  }
}

// ---------------------------------------------------------------- exclusão
function pedirExclusao(codigo: number) {
  pacienteAExcluir.value = pacientes.value.find((p) => p.codigo === codigo) || null;
}

async function confirmarExclusao() {
  if (!pacienteAExcluir.value) return;
  excluindo.value = true;
  try {
    await api.delete(`/api/pacientes/${pacienteAExcluir.value.codigo}`);
    toast.success(`Paciente ${pacienteAExcluir.value.nome} excluído.`);
    pacienteAExcluir.value = null;
    if (pacientes.value.length === 1 && pagina.value > 0) pagina.value -= 1;
    await carregarPacientes();
  } catch (error) {
    toast.error(mensagemErro(error, 'Não foi possível excluir o paciente.'));
  } finally {
    excluindo.value = false;
  }
}

onMounted(async () => {
  await carregarCapacidades();
  await carregarPacientes();
});
</script>
