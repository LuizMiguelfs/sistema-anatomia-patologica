<template>
  <section class="space-y-5">
    <div>
      <h1 class="text-2xl font-bold">Consulta de pacientes</h1>
      <p class="mt-1 text-sm text-gray-600">
        Dados cadastrais provenientes do AGHU. O SAP é somente leitura;
        cadastros e correções devem ser realizados nos sistemas oficiais do hospital.
      </p>
      <div class="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
        <strong>Fonte ativa:</strong> {{ fonte }}.
        {{ fonte === 'CSV' ? 'Ambiente offline de demonstração — não corresponde ao AGHU.' : 'Cadastro e atualização não são permitidos nesta plataforma.' }}
      </div>
    </div>

    <form class="flex flex-wrap gap-3 rounded-lg border bg-white p-4" @submit.prevent="pesquisar">
      <label class="sr-only" for="busca-paciente">Nome ou código do paciente</label>
      <input id="busca-paciente" v-model="termo" class="min-w-52 flex-1 rounded border p-2 text-sm"
             placeholder="Buscar por nome (mín. 3 letras) ou código" maxlength="100" />
      <button type="submit" :disabled="carregando" class="rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Buscar</button>
      <button type="button" class="rounded border px-4 py-2 text-sm" @click="limpar">Limpar</button>
    </form>

    <p v-if="erro" role="alert" class="rounded bg-red-50 p-3 text-sm text-red-700">{{ erro }}</p>

    <div class="overflow-x-auto rounded-lg border bg-white">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-gray-700">
          <tr><th class="px-4 py-3">Código AGHU</th><th class="px-4 py-3">Nome</th><th class="px-4 py-3">Nascimento</th><th class="px-4 py-3">Sexo</th><th class="px-4 py-3">Detalhes</th></tr>
        </thead>
        <tbody class="divide-y">
          <tr v-for="p in pacientes" :key="p.codigo">
            <td class="px-4 py-3 font-mono">{{ p.codigo }}</td>
            <td class="px-4 py-3">{{ p.nome }}</td>
            <td class="px-4 py-3">{{ formatarNascimento(p.dt_nascimento) }}</td>
            <td class="px-4 py-3">{{ p.sexo || '—' }}</td>
            <td class="px-4 py-3"><button type="button" class="font-semibold text-blue-700 underline" @click="detalhe = p">Visualizar</button></td>
          </tr>
          <tr v-if="!carregando && !pacientes.length"><td colspan="5" class="px-4 py-5 text-center text-gray-500">Nenhum paciente encontrado.</td></tr>
          <tr v-if="carregando"><td colspan="5" class="px-4 py-5 text-center text-gray-500">Carregando…</td></tr>
        </tbody>
      </table>
    </div>
    <div class="flex items-center justify-between text-sm text-gray-600">
      <span>Página {{ pagina + 1 }}</span>
      <div class="flex gap-2">
        <button type="button" class="rounded border px-4 py-2 disabled:opacity-50" :disabled="pagina === 0 || carregando" @click="irPagina(pagina - 1)">Anterior</button>
        <button type="button" class="rounded border px-4 py-2 disabled:opacity-50" :disabled="!haProxima || carregando" @click="irPagina(pagina + 1)">Próxima</button>
      </div>
    </div>

    <div v-if="detalhe" role="dialog" aria-modal="true" aria-label="Detalhes do paciente" class="rounded-lg border bg-white p-5 shadow">
      <div class="flex justify-between gap-3">
        <h2 class="font-semibold">Dados cadastrais — somente leitura</h2>
        <button type="button" class="text-sm text-blue-700 underline" @click="detalhe = null">Fechar</button>
      </div>
      <dl class="mt-3 grid gap-3 text-sm sm:grid-cols-2">
        <div><dt class="text-gray-500">Código AGHU</dt><dd>{{ detalhe.codigo }}</dd></div>
        <div><dt class="text-gray-500">Nome</dt><dd>{{ detalhe.nome }}</dd></div>
        <div><dt class="text-gray-500">Nascimento</dt><dd>{{ formatarNascimento(detalhe.dt_nascimento) }}</dd></div>
        <div><dt class="text-gray-500">Sexo</dt><dd>{{ detalhe.sexo || '—' }}</dd></div>
        <div><dt class="text-gray-500">Nome da mãe</dt><dd>{{ detalhe.nome_mae || '—' }}</dd></div>
        <div><dt class="text-gray-500">Nome do pai</dt><dd>{{ detalhe.nome_pai || '—' }}</dd></div>
      </dl>
      <p class="mt-4 text-xs text-gray-500">Se houver divergência, solicitar correção no AGHU; o SAP não altera cadastros.</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import api from '../services/api';

interface Paciente {
  codigo: number;
  nome: string;
  dt_nascimento: string | null;
  sexo: string | null;
  nome_mae: string | null;
  nome_pai: string | null;
}
const LIMITE = 20;
const pacientes = ref<Paciente[]>([]);
const detalhe = ref<Paciente | null>(null);
const termo = ref('');
const pagina = ref(0);
const fonte = ref('—');
const erro = ref('');
const carregando = ref(false);
const haProxima = ref(false);

const formatarNascimento = (iso: string | null) => iso
  ? new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString('pt-BR') : '—';
const mensagemErro = (e: unknown) => {
  const erroApi = e as { response?: { data?: { detail?: string } } };
  return erroApi?.response?.data?.detail || 'Não foi possível consultar o cadastro de pacientes.';
};

async function carregar() {
  carregando.value = true;
  erro.value = '';
  detalhe.value = null;
  try {
    // Busca um elemento extra apenas para indicar a existência de próxima página.
    const { data } = await api.get<Paciente[]>('/api/pacientes', {
      params: { termo: termo.value.trim() || undefined, limite: LIMITE + 1, offset: pagina.value * LIMITE },
    });
    haProxima.value = data.length > LIMITE;
    pacientes.value = data.slice(0, LIMITE);
  } catch (e) {
    pacientes.value = [];
    erro.value = mensagemErro(e);
  } finally {
    carregando.value = false;
  }
}
function pesquisar() {
  pagina.value = 0;
  void carregar();
}
function limpar() {
  termo.value = '';
  pesquisar();
}
function irPagina(n: number) {
  pagina.value = n;
  void carregar();
}
onMounted(async () => {
  try {
    const { data } = await api.get<{ fonte: string }>('/api/pacientes/capacidades');
    fonte.value = data.fonte === 'POSTGRES' ? 'AGHU' : data.fonte;
  } catch { fonte.value = 'Indisponível'; }
  await carregar();
});
</script>
