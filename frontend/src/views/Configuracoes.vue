<template>
  <div class="space-y-6">
    <!-- Perfil do usuário logado (todos os perfis) -->
    <Card>
      <template #header>
        <div class="flex items-center space-x-3">
          <Cog6ToothIcon class="h-7 w-7 text-paper-text" />
          <h1 class="text-2xl font-bold text-paper-text">Configurações</h1>
        </div>
      </template>

      <div v-if="authStore.user" class="p-5 bg-white border border-gray-200 rounded-xl shadow-sm space-y-3">
        <div class="flex items-center space-x-2 text-paper-text font-bold text-lg border-b pb-2">
          <UserCircleIcon class="h-6 w-6 text-gray-500" />
          <span>Seu perfil</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4 text-sm pt-1">
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase">Login de rede</p>
            <p class="font-bold text-gray-800">{{ authStore.user.username }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase">Nome</p>
            <p class="font-medium text-gray-800">{{ authStore.user.displayName?.[0] || authStore.user.username }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase">E-mail</p>
            <p class="font-medium text-gray-800">{{ authStore.user.email?.[0] || 'Não cadastrado' }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase">Setor</p>
            <p class="font-medium text-gray-800">{{ authStore.user.department?.[0] || '—' }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase">Perfil no SAP</p>
            <p class="font-medium text-gray-800">{{ rotuloPerfil(authStore.user.role) }}</p>
          </div>
        </div>
      </div>
    </Card>

    <!-- Gestão de usuários (somente Chefia; o backend também restringe) -->
    <Card v-if="authStore.isChefia">
      <template #header>
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div class="flex items-center space-x-3">
            <UserGroupIcon class="h-6 w-6 text-paper-text" />
            <div>
              <h2 class="text-lg font-bold text-paper-text">Usuários do SAP</h2>
              <p class="text-xs text-gray-500">Quem acessa o sistema e com qual perfil. Não há exclusão: o acesso é inativado.</p>
            </div>
          </div>
          <Button variant="primary" @click="abrirInclusao">
            <span class="flex items-center gap-1"><UserPlusIcon class="h-5 w-5" /> Incluir usuário</span>
          </Button>
        </div>
      </template>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm text-gray-600">
          <thead class="bg-gray-50 text-xs uppercase font-semibold text-gray-500 border-b">
            <tr>
              <th class="py-3 px-4">Login de rede</th>
              <th class="py-3 px-4">Nome</th>
              <th class="py-3 px-4">Perfil</th>
              <th class="py-3 px-4 text-center">Situação</th>
              <th class="py-3 px-4 text-right">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="!usuarios.length">
              <td colspan="5" class="py-6 text-center text-gray-400">{{ carregandoUsuarios ? 'Carregando...' : 'Nenhum usuário cadastrado.' }}</td>
            </tr>
            <tr v-for="u in usuarios" :key="u.username" class="hover:bg-gray-50/80">
              <td class="py-3 px-4 font-bold text-gray-800">
                {{ u.username }}
                <span v-if="ehVoce(u)" class="ml-1 text-xs font-normal text-gray-400">(você)</span>
              </td>
              <td class="py-3 px-4">{{ u.nome || '—' }}</td>
              <td class="py-3 px-4">{{ rotuloPerfil(u.perfil) }}</td>
              <td class="py-3 px-4 text-center">
                <span :class="u.ativo ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'" class="px-2 py-0.5 text-xs font-bold rounded">
                  {{ u.ativo ? 'ATIVO' : 'INATIVO' }}
                </span>
              </td>
              <td class="py-3 px-4 text-right space-x-2 whitespace-nowrap">
                <!-- Ninguém altera o próprio perfil nem inativa a si mesmo (regra do backend). -->
                <button
                  type="button"
                  class="px-2.5 py-1 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded-md disabled:opacity-40 disabled:cursor-not-allowed"
                  :disabled="ehVoce(u) || salvando"
                  :title="ehVoce(u) ? 'Você não pode alterar o próprio perfil' : 'Alterar perfil'"
                  @click="abrirTrocaPerfil(u)"
                >Alterar perfil</button>
                <button
                  type="button"
                  :class="u.ativo ? 'text-red-600 hover:bg-red-50 border-red-200' : 'text-emerald-600 hover:bg-emerald-50 border-emerald-200'"
                  class="px-2.5 py-1 text-xs font-semibold border rounded-md disabled:opacity-40 disabled:cursor-not-allowed"
                  :disabled="ehVoce(u) || salvando"
                  @click="confirmacao = u"
                >{{ u.ativo ? 'Inativar' : 'Reativar' }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Perfis disponíveis (informativo) -->
      <div class="mt-5 p-4 bg-gray-50 border border-gray-200 rounded-xl">
        <div class="flex items-center space-x-2 text-paper-text font-bold text-sm border-b pb-2 mb-3">
          <ShieldCheckIcon class="h-5 w-5 text-gray-600" />
          <span>Perfis do SAP</span>
        </div>
        <dl class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div v-for="p in PERFIS_SAP" :key="p.valor" class="p-3 bg-white border border-gray-200 rounded-lg">
            <dt class="text-xs font-bold text-gray-800">{{ p.rotulo }}</dt>
            <dd class="text-xs text-gray-500 pt-1 leading-relaxed">{{ p.descricao }}</dd>
          </div>
        </dl>
      </div>
    </Card>

    <!-- Trilha de auditoria (TI e Chefia). O backend faz a checagem de permissão. -->
    <Card v-if="podeVerAuditoria">
      <template #header>
        <div class="flex items-center space-x-3">
          <ClipboardDocumentListIcon class="h-6 w-6 text-paper-text" />
          <div>
            <h2 class="text-lg font-bold text-paper-text">Trilha de auditoria</h2>
            <p class="text-xs text-gray-500">Registro imutável de quem fez o quê, quando e de onde. Somente leitura.</p>
          </div>
        </div>
      </template>
      <TrilhaAuditoria />
    </Card>

    <!-- Modal: incluir usuário -->
    <Modal :show="mostrarInclusao" @close="fecharInclusao">
      <template #header>Incluir usuário no SAP</template>
      <form class="space-y-4" @submit.prevent="salvarInclusao">
        <div>
          <label for="novo-login" class="block text-sm font-semibold text-gray-700 mb-1">Login de rede</label>
          <div class="flex gap-2">
            <input
              id="novo-login"
              v-model="novoLogin"
              type="text"
              maxlength="128"
              required
              placeholder="ex.: joao.silva"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-paper-text focus:outline-none text-sm"
              @input="resultadoAD = null; erroAD = ''"
              @keydown.enter.prevent="consultarAD"
            />
            <Button variant="info" type="button" :loading="consultandoAD" :disabled="!novoLogin.trim()" @click="consultarAD">
              <span class="flex items-center gap-1 text-xs font-semibold"><MagnifyingGlassIcon class="h-4 w-4" /> Consultar no AD</span>
            </Button>
          </div>
          <p class="text-xs text-gray-400 mt-1">O nome é preenchido a partir do Active Directory.</p>
        </div>

        <div v-if="resultadoAD" class="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs space-y-1">
          <p class="font-bold flex items-center gap-1 text-sm text-emerald-900">
            <CheckCircleIcon class="h-4 w-4 text-emerald-600 shrink-0" /> Login encontrado no Active Directory
          </p>
          <p><strong>Nome:</strong> {{ resultadoAD.displayName }}</p>
          <p v-if="resultadoAD.email"><strong>E-mail:</strong> {{ resultadoAD.email }}</p>
          <p v-if="resultadoAD.department"><strong>Setor:</strong> {{ resultadoAD.department }}</p>
        </div>
        <div v-if="erroAD" class="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs flex items-center gap-2">
          <ExclamationTriangleIcon class="h-4 w-4 text-red-500 shrink-0" />
          <span>{{ erroAD }}</span>
        </div>

        <div>
          <label for="novo-perfil" class="block text-sm font-semibold text-gray-700 mb-1">Perfil</label>
          <select id="novo-perfil" v-model="novoPerfil" required class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white">
            <option v-for="p in PERFIS_SAP" :key="p.valor" :value="p.valor">{{ p.rotulo }}</option>
          </select>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t">
          <Button variant="default" type="button" @click="fecharInclusao">Cancelar</Button>
          <Button variant="primary" type="submit" :loading="salvando" :disabled="!resultadoAD">Incluir</Button>
        </div>
      </form>
    </Modal>

    <!-- Modal: alterar perfil -->
    <Modal :show="!!trocaPerfil" @close="trocaPerfil = null">
      <template #header>Alterar perfil</template>
      <form v-if="trocaPerfil" class="space-y-4" @submit.prevent="salvarPerfil">
        <div class="p-3 bg-gray-50 border rounded-lg space-y-1 text-sm">
          <p><strong class="text-gray-700">Login:</strong> {{ trocaPerfil.username }}</p>
          <p><strong class="text-gray-700">Nome:</strong> {{ trocaPerfil.nome || '—' }}</p>
          <p><strong class="text-gray-700">Perfil atual:</strong> {{ rotuloPerfil(trocaPerfil.perfil) }}</p>
        </div>
        <div>
          <label for="troca-perfil" class="block text-sm font-semibold text-gray-700 mb-1">Novo perfil</label>
          <select id="troca-perfil" v-model="perfilEscolhido" required class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white">
            <option v-for="p in PERFIS_SAP" :key="p.valor" :value="p.valor">{{ p.rotulo }}</option>
          </select>
        </div>
        <div class="flex justify-end space-x-3 pt-4 border-t">
          <Button variant="default" type="button" @click="trocaPerfil = null">Cancelar</Button>
          <Button variant="primary" type="submit" :loading="salvando" :disabled="perfilEscolhido === trocaPerfil.perfil">Salvar</Button>
        </div>
      </form>
    </Modal>

    <!-- Modal: confirmar inativação/reativação -->
    <Modal :show="!!confirmacao" @close="confirmacao = null">
      <template #header>{{ confirmacao?.ativo ? 'Inativar acesso' : 'Reativar acesso' }}</template>
      <p v-if="confirmacao" class="text-sm text-gray-700">
        <template v-if="confirmacao.ativo">
          <strong>{{ confirmacao.nome || confirmacao.username }}</strong> perde o acesso ao SAP imediatamente.
          O cadastro e o histórico continuam guardados, e o acesso pode ser reativado depois.
        </template>
        <template v-else>
          <strong>{{ confirmacao.nome || confirmacao.username }}</strong> volta a acessar o SAP com o perfil
          {{ rotuloPerfil(confirmacao.perfil) }}.
        </template>
      </p>
      <template #footer>
        <Button variant="default" @click="confirmacao = null">Cancelar</Button>
        <Button :variant="confirmacao?.ativo ? 'danger' : 'success'" :loading="salvando" @click="salvarSituacao">
          {{ confirmacao?.ativo ? 'Inativar' : 'Reativar' }}
        </Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
/**
 * Configurações: perfil do usuário logado, gestão de usuários do SAP (Chefia)
 * e trilha de auditoria (TI e Chefia). As permissões são sempre checadas no backend.
 */
import { computed, onMounted, ref } from 'vue';
import { useToast } from 'vue-toastification';
import Card from '../components/Card.vue';
import Modal from '../components/Modal.vue';
import Button from '../components/Button.vue';
import TrilhaAuditoria from '../components/TrilhaAuditoria.vue';
import { useAuthStore } from '../stores/auth';
import type { SapRole } from '../stores/auth';
import {
  PERFIS_SAP, alterarPerfil, alterarSituacao, buscarNoAD, incluirUsuario, listarUsuarios,
  mensagemDeErro, normalizarLogin, rotuloPerfil,
} from '../services/usuarios';
import type { UsuarioAD, UsuarioSap } from '../services/usuarios';
import {
  CheckCircleIcon,
  ClipboardDocumentListIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  UserCircleIcon,
  UserGroupIcon,
  UserPlusIcon,
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();
const toast = useToast();

/** Trilha de auditoria: TI (grupo do AD) ou Chefia (perfil local). */
const podeVerAuditoria = computed(() => authStore.isAdmin || authStore.isChefia);

const usuarios = ref<UsuarioSap[]>([]);
const carregandoUsuarios = ref(false);
const salvando = ref(false);

const mostrarInclusao = ref(false);
const novoLogin = ref('');
const novoPerfil = ref<SapRole>('RECEPCAO');
const consultandoAD = ref(false);
const resultadoAD = ref<UsuarioAD | null>(null);
const erroAD = ref('');

const trocaPerfil = ref<UsuarioSap | null>(null);
const perfilEscolhido = ref<SapRole>('RECEPCAO');
const confirmacao = ref<UsuarioSap | null>(null);

/** True quando a linha é o próprio usuário logado (ações bloqueadas). */
function ehVoce(u: UsuarioSap): boolean {
  return u.username === authStore.user?.username;
}

/** Recarrega a lista de usuários autorizados. */
async function carregarUsuarios() {
  carregandoUsuarios.value = true;
  try {
    usuarios.value = await listarUsuarios();
  } catch (erro) {
    toast.error(mensagemDeErro(erro, 'Falha ao carregar os usuários.'));
  } finally {
    carregandoUsuarios.value = false;
  }
}

/** Abre o modal de inclusão com o formulário limpo. */
function abrirInclusao() {
  novoLogin.value = '';
  novoPerfil.value = 'RECEPCAO';
  resultadoAD.value = null;
  erroAD.value = '';
  mostrarInclusao.value = true;
}

/** Fecha o modal de inclusão. */
function fecharInclusao() {
  mostrarInclusao.value = false;
}

/**
 * Confere o login no AD antes de liberar a inclusão.
 * Login inexistente ou desativado no AD não pode ser incluído.
 */
async function consultarAD() {
  const login = normalizarLogin(novoLogin.value);
  if (!login) return;
  consultandoAD.value = true;
  resultadoAD.value = null;
  erroAD.value = '';
  try {
    const dados = await buscarNoAD(login);
    if (dados.exists) resultadoAD.value = dados;
    else erroAD.value = `O login '${login}' não foi encontrado no Active Directory.`;
  } catch (erro) {
    erroAD.value = mensagemDeErro(erro, 'Falha ao consultar o Active Directory. Tente novamente.');
  } finally {
    consultandoAD.value = false;
  }
}

/** Inclui o login consultado no AD com o perfil escolhido e recarrega a lista. */
async function salvarInclusao() {
  if (!resultadoAD.value) return;
  salvando.value = true;
  try {
    const criado = await incluirUsuario(novoLogin.value, novoPerfil.value);
    toast.success(`${criado.nome || criado.username} incluído(a) como ${rotuloPerfil(criado.perfil)}.`);
    fecharInclusao();
    await carregarUsuarios();
  } catch (erro) {
    toast.error(mensagemDeErro(erro, 'Falha ao incluir o usuário.'));
  } finally {
    salvando.value = false;
  }
}

/** Abre o modal de troca de perfil já com o perfil atual selecionado. */
function abrirTrocaPerfil(u: UsuarioSap) {
  trocaPerfil.value = u;
  perfilEscolhido.value = u.perfil;
}

/** Grava o novo perfil (o backend recusa o próprio usuário) e recarrega a lista. */
async function salvarPerfil() {
  if (!trocaPerfil.value) return;
  salvando.value = true;
  try {
    const atualizado = await alterarPerfil(trocaPerfil.value.username, perfilEscolhido.value);
    toast.success(`Perfil de ${atualizado.username} alterado para ${rotuloPerfil(atualizado.perfil)}.`);
    trocaPerfil.value = null;
    await carregarUsuarios();
  } catch (erro) {
    toast.error(mensagemDeErro(erro, 'Falha ao alterar o perfil.'));
  } finally {
    salvando.value = false;
  }
}

/** Inativa ou reativa o acesso confirmado no modal e recarrega a lista. */
async function salvarSituacao() {
  const alvo = confirmacao.value;
  if (!alvo) return;
  salvando.value = true;
  try {
    const atualizado = await alterarSituacao(alvo.username, !alvo.ativo);
    toast.success(`Acesso de ${atualizado.username} ${atualizado.ativo ? 'reativado' : 'inativado'}.`);
    confirmacao.value = null;
    await carregarUsuarios();
  } catch (erro) {
    toast.error(mensagemDeErro(erro, 'Falha ao alterar a situação do acesso.'));
  } finally {
    salvando.value = false;
  }
}

onMounted(() => {
  if (authStore.isChefia) carregarUsuarios();
});
</script>
