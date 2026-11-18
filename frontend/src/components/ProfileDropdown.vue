<template>
  <div class="relative">
    <button type="button" class="h-10 w-10 rounded-full border border-gray-300 flex items-center justify-center"
      :aria-expanded="isOpen" aria-label="Abrir menu do perfil" @click="isOpen = !isOpen">
      <UserCircleIcon class="h-8 w-8 text-gray-600" />
    </button>
    <button v-if="isOpen" class="fixed inset-0 z-10 cursor-default" aria-label="Fechar menu do perfil" @click="isOpen = false" />
    <div v-if="isOpen" class="absolute right-0 z-20 mt-2 w-72 rounded-lg bg-white border border-gray-200 shadow-xl p-4 space-y-3">
      <div>
        <p class="font-semibold text-gray-900 break-words">{{ auth.nomeExibicao || 'Usuário' }}</p>
        <p class="text-sm text-gray-500 break-all">{{ auth.user?.username }}</p>
      </div>
      <div class="border-t pt-3 text-sm space-y-1">
        <p class="text-gray-500">Perfil de acesso</p>
        <p class="font-semibold text-gray-800">{{ auth.perfilRotulo ?? 'Não definido' }}</p>
        <p class="text-gray-500 pt-2">Setor</p>
        <p class="text-gray-800">{{ auth.user?.department?.[0] || 'Não informado' }}</p>
      </div>
      <button type="button" class="border-t pt-3 text-red-700 font-semibold text-sm w-full text-left"
        :disabled="leaving" @click="handleLogout">
        {{ leaving ? 'Encerrando sessão...' : 'Sair da conta' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { UserCircleIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '../stores/auth';

// O rótulo do perfil vem do store (mesma fonte de Configurações), não de uma lista própria.
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const isOpen = ref(false);
const leaving = ref(false);

async function handleLogout() {
  leaving.value = true;
  try { await auth.logout(router); }
  catch (_error) { await router.replace({ name: 'Login' }); }
  finally { leaving.value = false; isOpen.value = false; }
}
watch(() => route.path, () => { isOpen.value = false; });
</script>
