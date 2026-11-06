import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Configuracoes from '../views/Configuracoes.vue';
import Exemplos from '../views/Exemplos.vue';
import Pacientes from '../views/Pacientes.vue';

const routes = [
  {
    path: '/',
    name: 'Início',
    component: Home,
    meta: { requiresAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { layout: 'LoginLayout' },
  },
  {
    path: '/componentes',
    name: 'Componentes',
    component: Exemplos,
  },
  {
    path: '/exemplo',
    name: 'Exemplo',
    component: Pacientes,
    meta: { requiresAuth: true },
  },
  {
    path: '/configuracoes',
    name: 'Configuracoes',
    component: Configuracoes,
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Início', component: Home },
    { path: '/login', name: 'Login', component: Login, meta: { layout: 'LoginLayout', public: true } },
    { path: '/componentes', name: 'Componentes', component: Exemplos },
    { path: '/exemplo', name: 'Exemplo', component: Pacientes },
    { path: '/configuracoes', name: 'Configuracoes', component: Configuracoes },
  ],
  linkActiveClass: 'bg-paper-active-link',
  linkExactActiveClass: 'bg-paper-active-link',
});

router.beforeEach(async to => {
  const auth = useAuthStore();
  await auth.initializeAuth();
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'Login', query: { redirect: to.fullPath } };
  }
  if (to.meta.public && auth.isAuthenticated) return { name: 'Início' };
  return true;
});

export default router;
