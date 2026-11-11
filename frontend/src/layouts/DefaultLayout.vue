<template>
  <div class="relative h-screen overflow-hidden md:flex">
    <!-- Mobile Menu Header -->
    <div class="bg-paper-sidebar text-gray-100 flex justify-between md:hidden shrink-0">
      <router-link to="/" class="block p-4 text-white font-bold">{{ SYSTEM_TITLE }}</router-link>
      <button @click="sidebarOpen = !sidebarOpen" class="p-4 focus:outline-none focus:bg-paper-active-link">
        <Bars3Icon class="h-6 w-6" />
      </button>
    </div>

    <!-- Sidebar (Expansível / Recolhível) -->
    <aside 
      :class="[
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        isCollapsed ? 'md:w-20' : 'md:w-64'
      ]" 
      class="bg-paper-sidebar text-gray-100 pt-7 pb-2 px-2 absolute inset-y-0 left-0 transform md:relative md:translate-x-0 transition-all duration-300 ease-in-out z-20 h-full shrink-0 flex flex-col justify-between"
    >
      <div class="min-h-0 overflow-y-auto">
        <!-- Clique em "Nome do Sistema" recolhe/expande a barra lateral -->
        <div 
          @click="toggleSidebar" 
          title="Clique para recolher / expandir o menu"
          class="cursor-pointer text-white flex items-center space-x-3 px-3 mb-6 hover:opacity-90 transition duration-150 group"
        >
          <CubeTransparentIcon class="h-8 w-8 shrink-0 group-hover:scale-105 transition-transform" />
          <span v-if="!isCollapsed" class="text-xl font-extrabold leading-snug break-words select-none">
            {{ SYSTEM_TITLE }}
          </span>
        </div>

        <div class="px-3 my-4">
          <div class="border-t border-white border-opacity-20"></div>
        </div>

        <!-- Links de Navegação (agrupados como no MVP) -->
        <nav class="space-y-1">
          <router-link
            to="/"
            :title="isCollapsed ? 'Início' : ''"
            :class="[isCollapsed ? 'justify-center px-2' : 'px-4']"
            class="flex items-center space-x-3 py-2.5 rounded transition duration-200 hover:bg-paper-active-link hover:text-white"
          >
            <HomeIcon class="h-6 w-6 shrink-0"/>
            <span v-if="!isCollapsed" class="truncate">Início</span>
          </router-link>

          <template v-if="authStore.isAuthenticated">
            <template v-for="grupo in GRUPOS_MENU" :key="grupo.titulo">
              <p v-if="!isCollapsed" class="px-4 pt-4 pb-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                {{ grupo.titulo }}
              </p>
              <div v-else class="mx-3 my-2 border-t border-white border-opacity-20"></div>
              <router-link
                v-for="item in grupo.itens"
                :key="item.to"
                :to="item.to"
                :title="isCollapsed ? `${grupo.titulo}: ${item.rotulo}` : ''"
                :class="[isCollapsed ? 'justify-center px-2' : 'pl-6 pr-4']"
                class="flex items-center space-x-3 py-2 rounded text-sm transition duration-200 hover:bg-paper-active-link hover:text-white"
              >
                <component :is="item.icone" class="h-5 w-5 shrink-0" />
                <span v-if="!isCollapsed" class="truncate">{{ item.rotulo }}</span>
              </router-link>
            </template>

            <div class="mx-3 my-3 border-t border-white border-opacity-20"></div>
            <router-link
              to="/configuracoes"
              :title="isCollapsed ? 'Configurações' : ''"
              :class="[isCollapsed ? 'justify-center px-2' : 'px-4']"
              class="flex items-center space-x-3 py-2.5 rounded transition duration-200 hover:bg-paper-active-link hover:text-white"
            >
              <Cog6ToothIcon class="h-6 w-6 shrink-0"/>
              <span v-if="!isCollapsed" class="truncate">Configurações</span>
            </router-link>
          </template>
        </nav>
      </div>

      <!-- Rodapé de Versão da Sidebar -->
      <div v-if="!isCollapsed" class="px-4 pt-3 pb-1 border-t border-white/10 text-xs text-gray-400 mt-auto truncate transition-opacity duration-200">
        <p class="font-semibold text-gray-200 truncate">{{ APP_NAME }}</p>
        <p class="text-[11px] text-gray-400 truncate">Versão {{ APP_VERSION }} | HC-UFPE</p>
      </div>
      <div v-else class="px-2 pt-3 pb-1 border-t border-white/10 text-[10px] text-center text-gray-400 mt-auto">
        v{{ APP_VERSION }}
      </div>
    </aside>

    <!-- Content -->
    <div class="flex-1 flex flex-col bg-paper-bg overflow-y-auto h-full">
      <header class="flex justify-between items-center p-6 bg-white/80 backdrop-blur-md border-b border-gray-300 sticky top-0 z-10">
        <div>
          <h1 class="text-2xl font-semibold text-paper-text">{{ $route.name }}</h1>
        </div>
        <div>
          <router-link v-if="!authStore.isAuthenticated" to="/login">
            <Button variant="primary">
              <template #icon>
                <ArrowRightOnRectangleIcon class="h-5 w-5" />
              </template>
              Login
            </Button>
          </router-link>
          <ProfileDropdown v-else />
        </div>
      </header>
      <main class="flex-1">
        <div class="container py-4 md:py-6">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import {
  HomeIcon,
  Cog6ToothIcon,
  CubeTransparentIcon,
  Bars3Icon,
  ArrowRightOnRectangleIcon,
  InboxIcon,
  InboxArrowDownIcon,
  ArchiveBoxIcon,
  EyeIcon,
  BoltIcon,
  Squares2X2Icon,
  BeakerIcon,
  MagnifyingGlassIcon,
  DocumentMagnifyingGlassIcon,
} from '@heroicons/vue/24/outline';
import ProfileDropdown from '../components/ProfileDropdown.vue';
import Button from '../components/Button.vue';
import { useAuthStore } from '../stores/auth';
import { APP_VERSION, APP_NAME, SYSTEM_TITLE } from '../config/version';

/** Menu do MVP: Solicitações de Exames e as fases do setor (00-validacao-negocio / escopo do MVP). */
const GRUPOS_MENU = [
  {
    titulo: 'Solicitações de Exames',
    itens: [
      { to: '/solicitacoes/nao-retirados', rotulo: 'Não retirados', icone: InboxIcon },
      { to: '/solicitacoes/retirados', rotulo: 'Retirados', icone: InboxArrowDownIcon },
      { to: '/solicitacoes/arquivados', rotulo: 'Arquivados', icone: ArchiveBoxIcon },
    ],
  },
  {
    titulo: 'Fase Pré-Analítica',
    itens: [
      { to: '/fases/macroscopia', rotulo: 'Macroscopia', icone: EyeIcon },
      { to: '/fases/congelacao', rotulo: 'Congelação', icone: BoltIcon },
      { to: '/fases/processamento', rotulo: 'Processamento Técnico', icone: Squares2X2Icon },
      { to: '/fases/ihq', rotulo: 'IHQ', icone: BeakerIcon },
    ],
  },
  {
    titulo: 'Fase Analítica',
    itens: [
      { to: '/fases/microscopia', rotulo: 'Microscopia', icone: MagnifyingGlassIcon },
      { to: '/fases/revisao-de-lamina', rotulo: 'Revisão de Lâmina', icone: DocumentMagnifyingGlassIcon },
    ],
  },
];

const sidebarOpen = ref(false);
const isCollapsed = ref(false);

const route = useRoute();
const authStore = useAuthStore();

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value;
};

// Close mobile sidebar on route change
watch(() => route.path, () => {
  sidebarOpen.value = false;
});
</script>