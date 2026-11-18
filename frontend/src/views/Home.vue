<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import Card from '../components/Card.vue';
import api from '../services/api';
import {
  ROTA_NAO_RETIRADAS, fasesDoGrupo, locaisAguardandoPatologista, locaisComUrgentes, rotaDaFase,
  type RetratoFilas,
} from '../services/painel';
import { useAuthStore } from '../stores/auth';
import { useUiStore } from '../stores/ui';

import {
  ArrowPathIcon,
  BeakerIcon,
  ChartBarIcon,
  ClockIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  InboxStackIcon,
} from '@heroicons/vue/24/outline';

type OrigemDados =
  | 'demonstracao'
  | 'banco_dados'
  | 'indisponivel';

interface ResumoOperacional {
  total_solicitacoes: number | null;
  solicitacoes_pendentes: number | null;
  solicitacoes_atrasadas: number | null;
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
  prazo_cobertura_solicitacoes: number;
  filas?: RetratoFilas | null;
}

const ROTULOS: Record<string, string> = {
  total_solicitacoes: 'Total de solicitações',
  solicitacoes_pendentes: 'Solicitações pendentes',
  solicitacoes_atrasadas: 'Solicitações atrasadas',
  aguardando_complementacao: 'Aguardando complementação',
  tempo_medio_liberacao_horas: 'Tempo médio de liberação',
  percentual_cumprimento_prazo: 'Cumprimento de prazo',
  percentual_automacao: 'Automação de dados',
  percentual_rastreabilidade: 'Rastreabilidade',
  total_inconsistencias: 'Inconformidades abertas',
  total_rejeicoes: 'Rejeições',
  total_erros_transcricao: 'Erros de transcrição',
  filas: 'Filas agora',
};
const rotuloIndicador = (chave: string) => ROTULOS[chave] || chave;

const uiStore = useUiStore();
const authStore = useAuthStore();
/** O patologista vê primeiro o que espera a validação dele. */
const ehPatologista = computed(() => authStore.role === 'PRECEPTORIA');
const GRUPOS_DE_FASES = [
  { grupo: 'PRE_ANALITICA', rotulo: 'Fase Pré-Analítica' },
  { grupo: 'ANALITICA', rotulo: 'Fase Analítica' },
];

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

      <!-- Filas agora (T5.1): cada número abre a aba onde estão as solicitações contadas -->
      <section v-if="resumo.filas" class="space-y-4">
        <div class="flex items-center gap-2">
          <InboxStackIcon class="h-6 w-6 text-paper-text" />
          <h2 class="text-xl font-bold text-paper-text">Filas agora</h2>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <router-link
            :to="ROTA_NAO_RETIRADAS"
            class="block rounded-lg bg-white p-6 shadow-paper transition hover:ring-2 hover:ring-paper-primary/40"
          >
            <p class="text-sm font-medium text-gray-500">Não retiradas</p>
            <p class="mt-3 text-3xl font-bold text-gray-800">{{ formatarNumero(resumo.filas.nao_retiradas) }}</p>
            <p class="mt-2 text-xs text-gray-500">Recebidas no AGHU e ainda na Recepção.</p>
          </router-link>

          <div class="rounded-lg bg-white p-6 shadow-paper">
            <p class="text-sm font-medium text-gray-500">Urgentes pendentes</p>
            <p class="mt-3 text-3xl font-bold" :class="resumo.filas.urgentes ? 'text-red-700' : 'text-gray-800'">
              {{ formatarNumero(resumo.filas.urgentes) }}
            </p>
            <ul v-if="locaisComUrgentes(resumo.filas).length" class="mt-2 space-y-1 text-sm">
              <li v-for="local in locaisComUrgentes(resumo.filas)" :key="local.rota">
                <router-link :to="local.rota" class="text-red-700 underline-offset-2 hover:underline">
                  {{ local.rotulo }}: {{ local.quantidade }}
                </router-link>
              </li>
            </ul>
            <p v-else class="mt-2 text-xs text-gray-500">Nenhuma urgência pendente.</p>
          </div>

          <div
            class="rounded-lg bg-white p-6 shadow-paper"
            :class="ehPatologista ? 'ring-2 ring-paper-primary/50 md:order-first' : ''"
          >
            <p class="text-sm font-medium text-gray-500">
              {{ ehPatologista ? 'Aguardando sua validação' : 'Aguardando o patologista' }}
            </p>
            <p class="mt-3 text-3xl font-bold text-gray-800">{{ formatarNumero(resumo.filas.aguardando_patologista) }}</p>
            <ul v-if="locaisAguardandoPatologista(resumo.filas).length" class="mt-2 space-y-1 text-sm">
              <li v-for="local in locaisAguardandoPatologista(resumo.filas)" :key="local.rota">
                <router-link :to="local.rota" class="text-paper-default underline-offset-2 hover:underline">
                  {{ local.rotulo }}: {{ local.quantidade }}
                </router-link>
              </li>
            </ul>
            <p class="mt-2 text-xs text-gray-500">Pré-laudo salvo pelo residente, esperando validação e conclusão.</p>
          </div>
        </div>

        <div v-for="g in GRUPOS_DE_FASES" :key="g.grupo" class="space-y-2">
          <h3 class="text-sm font-semibold uppercase tracking-wide text-gray-500">{{ g.rotulo }}</h3>
          <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
            <router-link
              v-for="fase in fasesDoGrupo(resumo.filas, g.grupo)"
              :key="fase.etapa"
              :to="rotaDaFase(fase.etapa)"
              class="block rounded-lg bg-white p-4 shadow-paper transition hover:ring-2 hover:ring-paper-primary/40"
            >
              <p class="text-sm font-medium text-gray-600">{{ fase.rotulo }}</p>
              <p class="mt-2 text-2xl font-bold text-gray-800">
                {{ formatarNumero(fase.pendentes) }}
                <span class="text-sm font-normal text-gray-500">pendente(s)</span>
              </p>
              <p class="mt-1 flex flex-wrap gap-1 text-xs">
                <span v-if="fase.urgentes" class="rounded bg-red-600 px-1.5 py-0.5 font-bold uppercase text-white">
                  {{ fase.urgentes }} urgente(s)
                </span>
                <span v-if="fase.aguardando_patologista" class="rounded bg-blue-100 px-1.5 py-0.5 font-medium text-blue-800">
                  {{ fase.aguardando_patologista }} aguardando patologista
                </span>
              </p>
            </router-link>
          </div>
        </div>
      </section>

      <!-- SLA: a referência é explícita e precisa de homologação da Chefia -->
      <section class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm">
        <h2 class="font-semibold text-blue-900">Critério de prazo e cobertura</h2>
        <p class="mt-1 text-gray-700">
          Neste painel, “atrasada” é uma solicitação ainda aberta cujo tempo <strong>corrido desde a abertura no SAP</strong>
          superou o limite configurado para seu tipo. Não equivale automaticamente ao prazo clínico de liberação do laudo.
        </p>
        <p v-if="!Object.keys(resumo.prazos_horas_por_tipo || {}).length" class="mt-2 font-medium text-amber-800">
          Nenhum prazo aprovado foi configurado. Portanto, solicitações atrasadas e taxa de cumprimento não podem ser afirmados.
        </p>
        <div v-else class="mt-2">
          <p><strong>Prazos cadastrados:</strong>
            <span v-for="(horas, tipo) in resumo.prazos_horas_por_tipo" :key="tipo" class="mr-3">
              {{ tipo }}: {{ horas }} horas corridas
            </span>
          </p>
          <p class="mt-1">Solicitações pendentes cobertas por prazo:
            {{ resumo.prazo_cobertura_solicitacoes }} / {{ resumo.operacional.solicitacoes_pendentes ?? '—' }}.
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
              Total de solicitações
            </p>
            <p class="mt-3 text-3xl font-bold text-gray-800">
              {{ formatarNumero(resumo.operacional.total_solicitacoes) }}
            </p>
          </Card>

          <Card>
            <p class="text-sm font-medium text-gray-500">
              Solicitações pendentes
            </p>
            <p class="mt-3 text-3xl font-bold text-gray-800">
              {{ formatarNumero(resumo.operacional.solicitacoes_pendentes) }}
            </p>
          </Card>

          <Card>
            <p class="text-sm font-medium text-gray-500">
              Solicitações atrasadas
            </p>
            <p class="mt-3 text-3xl font-bold text-red-700">
              {{ formatarNumero(resumo.operacional.solicitacoes_atrasadas) }}
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
            <p class="mt-2 text-xs text-gray-500">
              Encaminhadas (IHQ, recorte, revisão, Rede Externa) que ainda não voltaram à etapa de origem.
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
              Inconformidades abertas
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