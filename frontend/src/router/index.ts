import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Pacientes from '../views/Pacientes.vue';
import Configuracoes from '../views/Configuracoes.vue';
import Casos from '../views/Casos.vue';

/** Fonte única de rotas. Funcionalidades ainda não integradas não aparecem no menu. */
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Início', component: Home, meta: { requiresAuth: true } },
    { path: '/login', name: 'Login', component: Login, meta: { layout: 'LoginLayout', public: true } },
    { path: '/pacientes', name: 'Pacientes', component: Pacientes, meta: { requiresAuth: true } },
    { path: '/casos', name: 'Casos', component: Casos, meta: { requiresAuth: true } },
    { path: '/configuracoes', name: 'Configurações', component: Configuracoes, meta: { requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  linkActiveClass: 'bg-paper-active-link',
  linkExactActiveClass: 'bg-paper-active-link',
});

router.beforeEach(async to => {
  const auth = useAuthStore();
  await auth.initializeAuth();
  // Default-Private: toda rota exige login, exceto as marcadas com meta.public.
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'Login', query: { redirect: to.fullPath } };
  }
  if (to.meta.public && auth.isAuthenticated) return { name: 'Início' };
  return true;
});

export default router;
