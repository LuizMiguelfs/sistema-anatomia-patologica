<script setup lang="ts">
import { onMounted, ref } from 'vue';
import Card from '../components/Card.vue';
import api from '../services/api';
import { useUiStore } from '../stores/ui';

import {
  ArrowPathIcon,
  BeakerIcon,
  ChartBarIcon,
  ClockIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
} from '@heroicons/vue/24/outline';

type OrigemDados =
  | 'demonstracao'
  | 'banco_dados'
  | 'indisponivel';

interface ResumoOperacional {
  total_casos: number | null;
  casos_pendentes: number | null;
  casos_atrasados: number | null;
  aguardando_complementacao: number | null;
}

interface IndicadoresGerenciais {
  tempo_medio_liberacao_horas: number | null;
  percentual_cumprimento_prazo: number | null;
  percentual_automacao: number | null;
  percentual_rastreabilidade: number | null;
  total_inconsistencias: number | null;
  total_rejeicoes: number | null;
  total_erros_transcricao: number | null;
}

interface DashboardResumo {
  origem_dados: OrigemDados;
  atualizado_em: string;
  operacional: ResumoOperacional;
  gerencial: IndicadoresGerenciais;
}

const uiStore = useUiStore();

const resumo = ref<DashboardResumo | null>(null);
const carregando = ref(false);
const erro = ref<string | null>(null);

const formatarNumero = (valor: number | null | undefined): string => {
  if (valor == null) return '—';

  return new Intl.NumberFormat('pt-BR').format(valor);
};

const formatarDecimal = (
  valor: number | null | undefined,
  sufixo = ''
): string => {
  if (valor == null) return '—';

  const numero = new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: 1,
  }).format(valor);

  return `${numero}${sufixo}`;
};

const formatarData = (valor: string): string => {
  const data = new Date(valor);

  if (Number.isNaN(data.getTime())) return '—';

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(data);
};

const carregarDashboard = async (): Promise<void> => {
  if (carregando.value) return;

  carregando.value = true;
  erro.value = null;
  uiStore.setLoading(true);

  try {
    const resposta = await api.get<DashboardResumo>(
      '/api/dashboard/resumo'
    );

    resumo.value = resposta.data;
  } catch (error) {
    console.error('Erro ao carregar dashboard:', error);

    resumo.value = null;
    erro.value =
      'Não foi possível carregar os indicadores. Verifique sua conexão e tente novamente.';
  } finally {
    carregando.value = false;
    uiStore.setLoading(false);
  }
};

onMounted(() => {
  void carregarDashboard();
});
</script>
<template>
  <div class="space-y-6">
    <!-- Cabeçalho -->
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <BeakerIcon class="h-8 w-8 text-paper-text" />
          <h1 class="text-2xl font-bold text-paper-text">
            Painel de Anatomia Patológica
          </h1>
        </div>

        <p class="mt-2 text-sm text-gray-600">
          Monitoramento operacional e indicadores gerenciais.
        </p>
      </div>

      <button
        type="button"
        :disabled="carregando"
        class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        @click="carregarDashboard"
      >
        <ArrowPathIcon
          class="h-5 w-5"
          :class="{ 'animate-spin': carregando }"
        />
        Atualizar
      </button>
    </div>

    <!-- Falha de carregamento -->
    <Card v-if="erro">
      <div
        role="alert"
        class="flex items-start gap-3 text-red-700"
      >
        <ExclamationTriangleIcon class="h-6 w-6 shrink-0" />

        <div>
          <h2 class="font-semibold">
            Não foi possível carregar o painel
          </h2>
          <p class="mt-1 text-sm">{{ erro }}</p>
        </div>
      </div>
    </Card>

    <!-- Estado inicial -->
    <Card v-else-if="!resumo">
      <p class="text-gray-600">
        Carregando informações do painel...
      </p>
    </Card>

    <template v-else>
      <!-- Identificação da origem dos dados -->
      <div
        v-if="resumo.origem_dados === 'demonstracao'"
        role="status"
        class="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900"
      >
        <strong>Ambiente demonstrativo:</strong>
        os indicadores apresentados são fictícios e não
        representam dados reais do HC-UFPE.
      </div>

      <div
        v-else-if="resumo.origem_dados === 'indisponivel'"
        role="status"
        class="rounded-lg border border-gray-300 bg-gray-50 p-4 text-sm text-gray-700"
      >
        Os indicadores ainda não estão disponíveis.
      </div>

      <div class="text-right text-xs text-gray-500">
        Atualizado em: {{ formatarData(resumo.atualizado_em) }}
      </div>

      <!-- Indicadores operacionais -->
      <section class="space-y-4">
        <div class="flex items-center gap-2">
          <DocumentTextIcon class="h-6 w-6 text-paper-text" />
          <h2 class="text-xl font-bold text-paper-text">
            Visão operacional
          </h2>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card>
            <p class="text-sm font-medium text-gray-500">
              Total de casos
            </p>
            <p class="mt-3 text-3xl font-bold text-gray-800">
              {{ formatarNumero(resumo.operacional.total_casos) }}
            </p>
          </Card>

          <Card>
            <p class="text-sm font-medium text-gray-500">
              Casos pendentes
            </p>
            <p class="mt-3 text-3xl font-bold text-gray-800">
              {{ formatarNumero(resumo.operacional.casos_pendentes) }}
            </p>
          </Card>

          <Card>
            <p class="text-sm font-medium text-gray-500">
              Casos atrasados
            </p>
            <p class="mt-3 text-3xl font-bold text-red-700">
              {{ formatarNumero(resumo.operacional.casos_atrasados) }}
            </p>
          </Card>

          <Card>
            <p class="text-sm font-medium text-gray-500">
              Aguardando complementação
            </p>
            <p class="mt-3 text-3xl font-bold text-amber-700">
              {{
                formatarNumero(
                  resumo.operacional.aguardando_complementacao
                )
              }}
            </p>
          </Card>
        </div>
      </section>

      <!-- Indicadores gerenciais -->
      <section class="space-y-4">
        <div class="flex items-center gap-2">
          <ChartBarIcon class="h-6 w-6 text-paper-text" />
          <h2 class="text-xl font-bold text-paper-text">
            Indicadores gerenciais
          </h2>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <div class="flex items-center gap-2">
              <ClockIcon class="h-5 w-5 text-gray-500" />
              <h3 class="font-semibold text-gray-800">
                Tempo médio de liberação
              </h3>
            </div>

            <p class="mt-4 text-3xl font-bold text-gray-800">
              {{
                formatarDecimal(
                  resumo.gerencial.tempo_medio_liberacao_horas,
                  ' h'
                )
              }}
            </p>

            <p class="mt-2 text-xs text-gray-500">
              Tempo médio entre recebimento da amostra
              e liberação do laudo.
            </p>
          </Card>

          <Card>
            <h3 class="font-semibold text-gray-800">
              Cumprimento de prazo
            </h3>

            <p class="mt-4 text-3xl font-bold text-gray-800">
              {{
                formatarDecimal(
                  resumo.gerencial.percentual_cumprimento_prazo,
                  '%'
                )
              }}
            </p>
          </Card>

          <Card>
            <h3 class="font-semibold text-gray-800">
              Automação de dados
            </h3>

            <p class="mt-4 text-3xl font-bold text-gray-800">
              {{
                formatarDecimal(
                  resumo.gerencial.percentual_automacao,
                  '%'
                )
              }}
            </p>
          </Card>

          <Card>
            <h3 class="font-semibold text-gray-800">
              Rastreabilidade
            </h3>

            <p class="mt-4 text-3xl font-bold text-gray-800">
              {{
                formatarDecimal(
                  resumo.gerencial.percentual_rastreabilidade,
                  '%'
                )
              }}
            </p>
          </Card>
        </div>
      </section>

      <!-- Indicadores complementares -->
      <section class="space-y-4">
        <h2 class="text-xl font-bold text-paper-text">
          Qualidade e inconsistências
        </h2>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card>
            <p class="text-sm text-gray-500">
              Inconsistências
            </p>
            <p class="mt-3 text-2xl font-bold text-gray-800">
              {{
                formatarNumero(
                  resumo.gerencial.total_inconsistencias
                )
              }}
            </p>
          </Card>

          <Card>
            <p class="text-sm text-gray-500">
              Rejeições
            </p>
            <p class="mt-3 text-2xl font-bold text-gray-800">
              {{
                formatarNumero(
                  resumo.gerencial.total_rejeicoes
                )
              }}
            </p>
          </Card>

          <Card>
            <p class="text-sm text-gray-500">
              Erros de transcrição
            </p>
            <p class="mt-3 text-2xl font-bold text-gray-800">
              {{
                formatarNumero(
                  resumo.gerencial.total_erros_transcricao
                )
              }}
            </p>
          </Card>
        </div>
      </section>
    </template>
  </div>
</template>