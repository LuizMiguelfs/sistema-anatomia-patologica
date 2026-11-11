import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Pacientes from '../views/Pacientes.vue';
import Configuracoes from '../views/Configuracoes.vue';
import Casos from '../views/Casos.vue';
import Solicitacoes from '../views/Solicitacoes.vue';
import Fase from '../views/Fase.vue';

/** Fonte única de rotas. Funcionalidades ainda não integradas não aparecem no menu. */
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Início', component: Home, meta: { requiresAuth: true } },
    { path: '/login', name: 'Login', component: Login, meta: { layout: 'LoginLayout', public: true } },
    { path: '/pacientes', name: 'Pacientes', component: Pacientes, meta: { requiresAuth: true } },
    { path: '/casos', name: 'Casos', component: Casos, meta: { requiresAuth: true } },
    { path: '/configuracoes', name: 'Configurações', component: Configuracoes, meta: { requiresAuth: true } },
    // Solicitações de Exames (MVP)
    { path: '/solicitacoes', redirect: '/solicitacoes/nao-retirados' },
    { path: '/solicitacoes/nao-retirados', name: 'Solicitações de Exames · Não retirados', component: Solicitacoes, meta: { requiresAuth: true, situacao: 'NAO_RETIRADO' } },
    { path: '/solicitacoes/retirados', name: 'Solicitações de Exames · Retirados', component: Solicitacoes, meta: { requiresAuth: true, situacao: 'RETIRADO' } },
    { path: '/solicitacoes/arquivados', name: 'Solicitações de Exames · Arquivados', component: Solicitacoes, meta: { requiresAuth: true, situacao: 'ARQUIVADO' } },
    // Fases do setor (MVP): uma tela genérica, a etapa vem do meta
    { path: '/fases/macroscopia', name: 'Fase Pré-Analítica · Macroscopia', component: Fase, meta: { requiresAuth: true, etapa: 'MACROSCOPIA' } },
    { path: '/fases/congelacao', name: 'Fase Pré-Analítica · Congelação', component: Fase, meta: { requiresAuth: true, etapa: 'CONGELACAO' } },
    { path: '/fases/processamento', name: 'Fase Pré-Analítica · Processamento Técnico', component: Fase, meta: { requiresAuth: true, etapa: 'PROCESSAMENTO' } },
    { path: '/fases/ihq', name: 'Fase Pré-Analítica · IHQ', component: Fase, meta: { requiresAuth: true, etapa: 'IHQ' } },
    { path: '/fases/microscopia', name: 'Fase Analítica · Microscopia', component: Fase, meta: { requiresAuth: true, etapa: 'MICROSCOPIA' } },
    { path: '/fases/revisao-de-lamina', name: 'Fase Analítica · Revisão de Lâmina', component: Fase, meta: { requiresAuth: true, etapa: 'REVISAO' } },
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
