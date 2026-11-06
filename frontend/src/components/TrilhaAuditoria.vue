<template>
  <div class="space-y-4">
    <!-- Filtros -->
    <form class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" @submit.prevent="buscar">
      <div>
        <label for="aud-usuario" class="form-label">Usuário</label>
        <input id="aud-usuario" v-model="filtros.usuario" maxlength="128" placeholder="ex.: joao.silva" class="form-control" />
      </div>
      <div>
        <label for="aud-categoria" class="form-label">Categoria</label>
        <select id="aud-categoria" v-model="filtros.categoria" class="form-control">
          <option value="">Todas</option>
          <option v-for="c in categorias" :key="c.valor" :value="c.valor">{{ c.rotulo }}</option>
        </select>
      </div>
      <div>
        <label for="aud-acao" class="form-label">Ação</label>
        <input id="aud-acao" v-model="filtros.acao" maxlength="100" placeholder="ex.: ALTERAR_PACIENTE" class="form-control" />
      </div>
      <div>
        <label for="aud-recurso" class="form-label">Recurso</label>
        <input id="aud-recurso" v-model="filtros.recurso" maxlength="200" placeholder="paciente:123 ou paciente:*" class="form-control" />
      </div>
      <div>
        <label for="aud-inicio" class="form-label">De</label>
        <input id="aud-inicio" v-model="filtros.data_inicio" type="date" :max="filtros.data_fim || undefined" class="form-control" />
      </div>
      <div>
        <label for="aud-fim" class="form-label">Até</label>
        <input id="aud-fim" v-model="filtros.data_fim" type="date" :min="filtros.data_inicio || undefined" class="form-control" />
      </div>
      <div class="sm:col-span-2 lg:col-span-3 flex justify-end gap-2">
        <Button type="button" variant="default" :disabled="carregando" @click="limpar">Limpar</Button>
        <Button type="submit" variant="success" :loading="carregando">Filtrar</Button>
      </div>
    </form>

    <!-- Resultados -->
    <DataTable :headers="headers" :items="linhas">
      <template #actions="{ item }">
        <Button variant="info" class="!py-1 !px-2" title="Ver antes e depois" @click="abrirDetalhe(item.id)">
          <EyeIcon class="h-4 w-4" />
        </Button>
      </template>
    </DataTable>

    <div class="flex items-center justify-between text-sm text-gray-600">
      <span>{{ resumoPagina }}</span>
      <div class="flex space-x-2">
        <Button variant="default" class="!py-1" :disabled="offset === 0 || carregando" @click="mudarPagina(-1)">Anterior</Button>
        <Button variant="default" class="!py-1" :disabled="offset + TAMANHO_PAGINA >= total || carregando" @click="mudarPagina(1)">Próxima</Button>
      </div>
    </div>

    <!-- Detalhe: antes e depois -->
    <Modal :show="!!detalhe" @close="detalhe = null">
      <template #header>Registro #{{ detalhe?.id }}</template>
      <div v-if="detalhe" class="space-y-4 text-sm">
        <dl class="grid grid-cols-2 gap-x-4 gap-y-2">
          <div><dt class="font-medium text-gray-500">Data/hora</dt><dd>{{ formatarDataHora(detalhe.created_at) }}</dd></div>
          <div><dt class="font-medium text-gray-500">Usuário</dt><dd>{{ detalhe.usuario }}</dd></div>
          <div><dt class="font-medium text-gray-500">Categoria</dt><dd>{{ rotuloCategoria(detalhe.categoria) }}</dd></div>
          <div><dt class="font-medium text-gray-500">IP de origem</dt><dd>{{ detalhe.ip_origem || '—' }}</dd></div>
          <div class="col-span-2"><dt class="font-medium text-gray-500">Ação</dt><dd class="font-mono">{{ detalhe.acao }}</dd></div>
          <div class="col-span-2"><dt class="font-medium text-gray-500">Recurso</dt><dd class="font-mono">{{ detalhe.recurso }}</dd></div>
        </dl>

        <!-- Comparação campo a campo quando antes/depois são objetos -->
        <div v-if="comparacao.length" class="overflow-x-auto border border-gray-200 rounded-lg">
          <table class="w-full text-xs">
            <thead class="bg-gray-50 text-gray-500 uppercase">
              <tr><th class="px-3 py-2 text-left">Campo</th><th class="px-3 py-2 text-left">Antes</th><th class="px-3 py-2 text-left">Depois</th></tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="linha in comparacao" :key="linha.campo" :class="linha.mudou ? 'bg-amber-50' : ''">
                <td class="px-3 py-2 font-medium">{{ linha.campo }}</td>
                <td class="px-3 py-2 break-all">{{ linha.antes }}</td>
                <td class="px-3 py-2 break-all" :class="linha.mudou ? 'font-semibold text-amber-900' : ''">{{ linha.depois }}</td>
              </tr>
            </tbody>
          </table>
          <p class="px-3 py-2 text-xs text-gray-500 bg-gray-50">Campos destacados foram alterados.</p>
        </div>

        <!-- Quando não são objetos, mostra o conteúdo bruto -->
        <div v-else class="grid grid-cols-1 gap-3">
          <div>
            <p class="font-medium text-gray-500 mb-1">Antes</p>
            <pre class="bg-gray-50 border border-gray-200 rounded p-2 text-xs overflow-auto max-h-48">{{ formatarJson(detalhe.dados_anteriores) }}</pre>
          </div>
          <div>
            <p class="font-medium text-gray-500 mb-1">Depois</p>
            <pre class="bg-gray-50 border border-gray-200 rounded p-2 text-xs overflow-auto max-h-48">{{ formatarJson(detalhe.dados_novos) }}</pre>
          </div>
        </div>
      </div>
      <template #footer>
        <Button variant="default" @click="detalhe = null">Fechar</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
/**
 * Trilha de auditoria (somente leitura): consulta GET /api/admin/auditoria.
 * O backend restringe o acesso à TI e à Chefia; esta tela não substitui essa checagem.
 */
import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import { EyeIcon } from '@heroicons/vue/24/outline';
import api from '../services/api';
import Button from './Button.vue';
import DataTable from './DataTable.vue';
import Modal from './Modal.vue';

interface RegistroAuditoria {
  id: number;
  created_at: string;
  usuario: string;
  categoria: string;
  acao: string;
  recurso: string;
  dados_anteriores: unknown;
  dados_novos: unknown;
  ip_origem: string | null;
}

interface PaginaAuditoria {
  total: number;
  limite: number;
  offset: number;
  itens: RegistroAuditoria[];
}

const TAMANHO_PAGINA = 20;

const categorias = [
  { valor: 'SEGURANCA', rotulo: 'Segurança' },
  { valor: 'NEGOCIO_CLINICO', rotulo: 'Negócio clínico' },
  { valor: 'CONFIGURACAO', rotulo: 'Configuração' },
];

const headers = [
  { text: 'Data/hora', value: 'quando' },
  { text: 'Usuário', value: 'usuario' },
  { text: 'Categoria', value: 'categoria' },
  { text: 'Ação', value: 'acao' },
  { text: 'Recurso', value: 'recurso' },
];

const toast = useToast();

const filtrosVazios = () => ({ usuario: '', categoria: '', acao: '', recurso: '', data_inicio: '', data_fim: '' });
const filtros = reactive(filtrosVazios());
const registros = ref<RegistroAuditoria[]>([]);
const total = ref(0);
const offset = ref(0);
const carregando = ref(false);
const detalhe = ref<RegistroAuditoria | null>(null);
let requisicaoAtual = 0;

const linhas = computed(() =>
  registros.value.map((r) => ({
    id: r.id,
    quando: formatarDataHora(r.created_at),
    usuario: r.usuario,
    categoria: rotuloCategoria(r.categoria),
    acao: r.acao,
    recurso: r.recurso,
  })),
);

const resumoPagina = computed(() => {
  if (total.value === 0) return 'Nenhum registro';
  const fim = Math.min(offset.value + TAMANHO_PAGINA, total.value);
  return `${offset.value + 1}–${fim} de ${total.value} registro(s)`;
});

type LinhaComparacao = { campo: string; antes: string; depois: string; mudou: boolean };

const comparacao = computed<LinhaComparacao[]>(() => {
  const d = detalhe.value;
  if (!d) return [];
  const antes = ehObjeto(d.dados_anteriores) ? d.dados_anteriores : null;
  const depois = ehObjeto(d.dados_novos) ? d.dados_novos : null;
  // Só compara campo a campo quando os lados existentes são objetos.
  if ((d.dados_anteriores != null && !antes) || (d.dados_novos != null && !depois) || (!antes && !depois)) return [];
  const campos = Array.from(new Set([...Object.keys(antes || {}), ...Object.keys(depois || {})]));
  return campos.map((campo) => {
    const a = antes ? formatarValor(antes[campo]) : '—';
    const b = depois ? formatarValor(depois[campo]) : '—';
    return { campo, antes: a, depois: b, mudou: a !== b };
  });
});

function ehObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === 'object' && valor !== null && !Array.isArray(valor);
}

function formatarValor(valor: unknown): string {
  if (valor === undefined || valor === null || valor === '') return '—';
  return typeof valor === 'object' ? JSON.stringify(valor) : String(valor);
}

function formatarJson(valor: unknown): string {
  if (valor === null || valor === undefined) return '—';
  return typeof valor === 'string' ? valor : JSON.stringify(valor, null, 2);
}

function formatarDataHora(iso: string): string {
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? iso : data.toLocaleString('pt-BR');
}

function rotuloCategoria(valor: string): string {
  return categorias.find((c) => c.valor === valor)?.rotulo || valor;
}

function mensagemErro(error: any, padrao: string): string {
  const detail = error?.response?.data?.detail;
  return typeof detail === 'string' ? detail : padrao;
}

async function carregar() {
  const id = ++requisicaoAtual;
  carregando.value = true;
  try {
    const params: Record<string, string | number> = {
      limite: TAMANHO_PAGINA,
      offset: offset.value,
      // Fuso do navegador: o filtro de datas considera o dia local (Recife = -180).
      utc_offset_minutos: -new Date().getTimezoneOffset(),
    };
    (Object.keys(filtros) as (keyof typeof filtros)[]).forEach((campo) => {
      const valor = filtros[campo].trim();
      if (valor) params[campo] = valor;
    });
    const { data } = await api.get<PaginaAuditoria>('/api/admin/auditoria', { params });
    if (id !== requisicaoAtual) return; // resposta antiga: descarta
    registros.value = data.itens;
    total.value = data.total;
  } catch (error) {
    if (id === requisicaoAtual) toast.error(mensagemErro(error, 'Falha ao carregar a trilha de auditoria.'));
  } finally {
    if (id === requisicaoAtual) carregando.value = false;
  }
}

function buscar() {
  offset.value = 0;
  carregar();
}

function limpar() {
  Object.assign(filtros, filtrosVazios());
  buscar();
}

function mudarPagina(delta: number) {
  offset.value = Math.max(0, offset.value + delta * TAMANHO_PAGINA);
  carregar();
}

function abrirDetalhe(id: number | string) {
  detalhe.value = registros.value.find((r) => r.id === Number(id)) || null;
}

onMounted(carregar);
</script>
