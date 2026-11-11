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
  criterios: Record<string, string>;
  prazos_horas_por_tipo: Record<string, number>;
  prazo_cobertura_casos: number;
}

const ROTULOS: Record<string, string> = {
  total_casos: 'Total de casos',
  casos_pendentes: 'Casos pendentes',
  casos_atrasados: 'Casos atrasados',
  aguardando_complementacao: 'Aguardando complementação',
  tempo_medio_liberacao_horas: 'Tempo médio de liberação',
  percentual_cumprimento_prazo: 'Cumprimento de prazo',
  percentual_automacao: 'Automação de dados',
  percentual_rastreabilidade: 'Rastreabilidade',
  total_inconsistencias: 'Inconformidades abertas',
  total_rejeicoes: 'Rejeições',
  total_erros_transcricao: 'Erros de transcrição',
};
const rotuloIndicador = (chave: string) => ROTULOS[chave] || chave;

const uiStore = useUiStore();

const resumo = ref<DashboardResumo | null>(null);
const carregando = ref(false);
const erro = ref<string | null>(null);

const formatarNumero = (valor: number | null | undefined): string => {
  if (valor == null) return 'Não medido';

  return new Intl.NumberFormat('pt-BR').format(valor);
};

const formatarDecimal = (
  valor: number | null | undefined,
  sufixo = ''
): string => {
  if (valor == null) return 'Não medido';

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

      <!-- SLA: a referência é explícita e precisa de homologação da Chefia -->
      <section class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm">
        <h2 class="font-semibold text-blue-900">Critério de prazo e cobertura</h2>
        <p class="mt-1 text-gray-700">
          Neste painel, “atrasado” é um caso ainda aberto cujo tempo <strong>corrido desde a abertura no SAP</strong>
          superou o limite configurado para seu tipo. Não equivale automaticamente ao prazo clínico de liberação do laudo.
        </p>
        <p v-if="!Object.keys(resumo.prazos_horas_por_tipo || {}).length" class="mt-2 font-medium text-amber-800">
          Nenhum prazo aprovado foi configurado. Portanto, casos atrasados e taxa de cumprimento não podem ser afirmados.
        </p>
        <div v-else class="mt-2">
          <p><strong>Prazos cadastrados:</strong>
            <span v-for="(horas, tipo) in resumo.prazos_horas_por_tipo" :key="tipo" class="mr-3">
              {{ tipo }}: {{ horas }} horas corridas
            </span>
          </p>
          <p class="mt-1">Casos pendentes cobertos por prazo:
            {{ resumo.prazo_cobertura_casos }} / {{ resumo.operacional.casos_pendentes ?? '—' }}.
            Quando a cobertura é incompleta, a contagem de atrasados fica indisponível.
          </p>
        </div>
      </section>

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

      <section class="space-y-3 rounded-lg border border-gray-200 bg-white p-5">
        <h2 class="text-xl font-bold text-paper-text">Dicionário de indicadores</h2>
        <p class="text-sm text-gray-600">
          Definições, população e limitações de cada número. “Não medido” significa que
          o dado necessário ainda não é capturado pelo sistema, não que o resultado seja zero.
        </p>
        <dl class="grid gap-3 md:grid-cols-2">
          <div v-for="(texto, chave) in resumo.criterios" :key="chave" class="rounded border border-gray-100 bg-gray-50 p-3">
            <dt class="text-sm font-semibold">{{ rotuloIndicador(chave) }}</dt>
            <dd class="mt-1 text-xs text-gray-600">{{ texto }}</dd>
          </div>
        </dl>
      </section>
    </template>
  </div>
</template>