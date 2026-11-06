<template>
  <div class="w-full">
    <Card>
      <template #header>
        <h1 class="text-xl font-semibold text-center">Acesso ao Serviço de Anatomia Patológica</h1>
      </template>
      <form @submit.prevent="handleLogin" class="space-y-5">
        <div>
          <label for="username" class="block text-sm font-semibold mb-2">Usuário de rede</label>
          <input id="username" v-model.trim="username" autocomplete="username" required
            class="border rounded w-full py-2 px-3" placeholder="usuario ou EBSERHNET\usuario" />
        </div>
        <div>
          <label for="password" class="block text-sm font-semibold mb-2">Senha corporativa</label>
          <div class="relative">
            <input id="password" v-model="password" autocomplete="current-password" required
              :type="showPassword ? 'text' : 'password'" class="border rounded w-full py-2 px-3 pr-24" />
            <button type="button" class="absolute right-2 top-2 text-sm text-gray-600"
              :aria-label="showPassword ? 'Ocultar senha' : 'Mostrar senha'" @click="showPassword = !showPassword">
              {{ showPassword ? 'Ocultar' : 'Mostrar' }}
            </button>
          </div>
        </div>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="rememberMe" type="checkbox" /> Manter acesso neste navegador
        </label>
        <p class="text-xs text-gray-600">Utilize apenas sua conta institucional. O acesso depende de autorização do setor.</p>
        <Button type="submit" variant="primary" :disabled="loading || !username || !password" class="w-full">
          {{ loading ? 'Autenticando...' : 'Entrar' }}
        </Button>
      </form>
    </Card>
    <p v-if="error" role="alert" aria-live="polite" class="mt-4 border border-red-300 bg-red-50 text-red-800 rounded px-4 py-3 text-sm">
      {{ error }}
    </p>
    <div class="mt-6 text-center text-xs text-gray-300 space-y-1">
      <p>{{ HOSPITAL_NAME }}</p>
      <p>{{ DEPARTMENT_NAME }} | Versão {{ APP_VERSION }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import Card from '../components/Card.vue';
import Button from '../components/Button.vue';
import { APP_VERSION, HOSPITAL_NAME, DEPARTMENT_NAME } from '../config/version';

const username = ref('');
const password = ref('');
const rememberMe = ref(false);
const showPassword = ref(false);
const loading = ref(false);
const error = ref('');
const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

async function handleLogin() {
  if (loading.value) return;
  loading.value = true;
  error.value = '';
  try {
    await auth.login(username.value, password.value, rememberMe.value);
    password.value = '';
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      && !route.query.redirect.startsWith('//') ? route.query.redirect : '/';
    await router.replace(redirect);
  } catch (e: any) {
    const status = e?.response?.status;
    error.value = status === 401 ? 'Usuário ou senha inválidos.'
      : status === 403 ? 'Conta sem autorização para o SAP. Contate a gestão do setor.'
      : status === 503 ? 'Autenticação institucional indisponível. Tente novamente mais tarde.'
      : 'Não foi possível iniciar a sessão.';
  } finally {
    password.value = '';
    loading.value = false;
  }
}
</script>
