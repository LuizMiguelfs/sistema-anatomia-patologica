# SPEC.md - Contrato de Desenvolvimento (SDD)

## 1. Visão Geral e Resultados Esperados
Este documento é a ÚNICA fonte de verdade para a orquestração do desenvolvimento. O objetivo é construir um sistema hospitalar seguro e em conformidade com a LGPD.

### Objetivos de Alto Nível
- [ ] Implementar autenticação via LDAP/AD (em desenvolvimento usa login simulado; a integração real depende da rede do hospital).
- [x] Consultar pacientes e solicitações no AGHU somente para leitura, sem editar a origem (RN-01).
- [x] Garantir trilhas de auditoria imutáveis.
- [ ] Acompanhar cada solicitação de exame da Recepção ao Arquivo (MVP entregue na v1.2.0: Solicitações de Exames, filas e formulários das fases, histórico e painel; formulários reais e Arquivados ainda pendentes).

## 2. Contexto do Projeto (Documentação Imutável)
As definições detalhadas estão distribuídas nos seguintes documentos:
- [Validação e Fluxo de Negócio](00-validacao-negocio.md) (Fase 0 - Negócio)
- [Visão](01-visao.md)
- [Requisitos](02-requisitos.md)
- [Casos de Uso](03-casos-uso.md)
- [Modelo de Dados](04-modelo-dados.md)
- [Interfaces](05-interfaces.md)
- [Arquitetura](06-arquitetura.md)
- [Glossário](07-glossario.md)

Os critérios de negócio estão em `02-requisitos.md` e `03-casos-uso.md`. Este arquivo **não substitui** requisitos clínicos e regras institucionais.

## 3. Limites de Escopo e Guardrails (Anti-Patterns)
**A IA DEVE:**
- Seguir rigorosamente o Modelo de Dados definido em `04-modelo-dados.md`.
- Implementar testes unitários para cada funcionalidade nova.
- Utilizar criptografia AES-256 para dados sensíveis.

**A IA NÃO DEVE:**
- Criar dependências externas não documentadas em `06-arquitetura.md`.
- Implementar exclusão física de registros (usar Soft Delete).
- Burlar o sistema de RBAC (Role-Based Access Control).

### Como as regras acima são aplicadas no código
| Regra | Aplicação |
|---|---|
| Testes para cada funcionalidade nova | Backend: `pytest` em `tests/`. Frontend: um `.spec.ts` (Vitest) para cada novo service ou store, ao lado do arquivo (`npm test`); componentes com regra de negócio também podem ter `.spec.ts` (ex.: `FormularioFase.spec.ts`). O CI (`.github/workflows/ci.yml`) roda tudo em cada PR. |
| AES-256 para dados sensíveis | AES-256-GCM em `src/helpers/crypto_helper.py`, chave em `SAP_DATA_KEY`. Cifra só o que identifica um único paciente (nome, nome da mãe e do pai, CPF, CNS, data de nascimento e prontuário), nas tabelas do SAP e no antes/depois da auditoria clínica (`CAMPOS_PACIENTE`). Busca exata por esses valores usa índice HMAC (`indice_busca`). |
| Dependências documentadas | Tabela "Dependências externas documentadas" do `06-arquitetura.md`, atualizada no mesmo commit que adiciona a dependência. |
| Sem exclusão física | Nenhum `DELETE` pela aplicação: registros são inativados ou marcados (`deleted_at`, `active`/`ativo`). A trilha `audit_logs` tem triggers que bloqueiam `UPDATE`/`DELETE`. |
| RBAC | Perfil lido do banco local a cada requisição (`auth_handler.decode_token`); rotas restritas com `auth_handler.require_roles(...)` ou checagem do perfil no controller. A matriz de perfis das solicitações e fases é conferida por `tests/test_matriz_perfis.py`. |

## 4. Task Breakdown (Plano de Implementação)
### Fase 1: Infraestrutura e Dados
- [x] [TASK-001] Validar esquemas de banco de dados conforme `04-modelo-dados.md` (migrações em linha única, testadas com dados).
- [x] [TASK-002] Configurar ambiente de auditoria de logs (trilha imutável, histórico por solicitação e trilha em Configurações).

### Fase 2: Funcionalidades Essenciais
- [ ] [TASK-003] Implementar Módulo de Autenticação (RF001): login, sessão, perfis e gestão de usuários prontos; falta homologar o AD real.
- [x] [TASK-004] Consulta de pacientes no AGHU (RF002), somente leitura. O cadastro local de pacientes saiu do escopo.

### Fase 3: MVP das solicitações de exame (v1.2.0)
- [x] Solicitações de Exames: Não retirados e Retirados, retirada pela Recepção.
- [x] Filas e formulários das fases (Salvar e Concluído), matriz de perfis e histórico da solicitação.
- [x] Início com o retrato das filas e indicadores que contam só o que o fluxo registra.
- [x] "Caso" renomeado para "solicitação de exame" no código e no banco.
- [ ] Formulários reais de cada fase (depois da reunião com o setor).
- [ ] Aba Arquivados.

### Divisão de responsabilidade
1. Autenticação, sessão, refresh e papéis: `src/auth`, `src/routers/auth.py`, `frontend/src/stores/auth.ts`.
2. Auditoria, logs, health e administração (inclui gestão de usuários): `src/models/audit_log.py`, `src/routers/admin.py`, `src/routers/auditoria.py`, `src/routers/usuarios.py`, `src/routers/health.py`, `frontend/src/views/Configuracoes.vue`, `frontend/src/components/TrilhaAuditoria.vue`, `frontend/src/components/LinhaDoTempo.vue`, `frontend/src/services/auditoria.ts`, `frontend/src/services/historico.ts`.
3. Pacientes e múltiplas fontes: `src/providers/*paciente*`, `src/controllers/paciente_controller.py` (API somente de consulta; a tela foi retirada).
4. Casos de uso centrais e workflow clínico: `src/routers/solicitacao.py`, `src/routers/retirada.py`, `src/routers/fase.py`, `src/controllers/solicitacao_controller.py`, `src/controllers/retirada_controller.py`, `src/controllers/fase_controller.py`, `src/providers/*solicitacao*` e `*aghu_solicitacao*`, `src/models/solicitacao.py`, `frontend/src/views/Solicitacoes.vue`, `frontend/src/views/Fase.vue`, `frontend/src/components/FormularioFase.vue`.
5. Dashboard e agregações: `src/routers/dashboard.py`, `src/providers/*dashboard*`, `src/providers/sql/solicitacao/dashboard_*.sql`, `frontend/src/views/Home.vue`, `frontend/src/services/painel.ts`.
6. Repositório, conexões, rotas, navegação, SQL compartilhado, migrações, CI (`.github/workflows/ci.yml`), documentação e validação conjunta.

## 5. Critérios de Verificação Global
- [ ] 100% de cobertura em rotas de autenticação.
- [ ] Zero vulnerabilidades críticas no lint de segurança.
- [ ] Conformidade total com os esquemas JSON/OpenAPI.

### Critérios para aceitar a integração
- [x] Rotas Vue reunidas em um único array com guarda de autenticação; páginas de exemplo retiradas.
- [x] Menu com Início, Solicitações de Exames, Fase Pré-Analítica, Fase Analítica e Configurações; rota de histórico de auditoria incluída na API.
- [x] Engines e sessões administradas pelo ciclo de vida do FastAPI.
- [x] `audit_framework.py` executa sem `NameError`.
- [x] Migrações com IDs encadeados em uma única linha e revisão intermediária não destrutiva para instalações novas.
- [x] `pytest -q` integral em ambiente com dependências instaladas e configurações de teste (CI em cada PR).
- [x] `npm ci && npm run build` (CI em cada PR) e navegação testada no navegador com a carga de demonstração.
- [ ] Migrações executadas e conferidas em cópia de banco real com backup.
- [x] Integração do módulo 4 com os outros membros (solicitações, fases, histórico e painel).
- [ ] Fluxos complementares (retornos entre etapas, envios externos, Arquivados) homologados com o setor.
- [ ] Testes reais de LDAP/AGHU, permissões, retenção e privacidade aprovados pela equipe responsável.

## 6. Regras de mudança
Nunca colocar `.env`, tokens, chaves (`JWT_SECRET`, `SAP_DATA_KEY`) ou dados reais de pacientes no Git. Os módulos não devem importar implementações concretas diretamente de outros módulos quando houver interface de Provider. Para SQL dinâmico de usuário, usar bind parameters, não substituição textual. Não apagar logs de auditoria. Revisar migrações com o time antes de aplicá-las em banco já utilizado.

## 7. Validação recomendada

```bash
uv run python audit_framework.py .
uv run pytest -q
cd frontend && npm ci && npm test && npm run build
uv run alembic heads
```

O CI (`.github/workflows/ci.yml`) roda os três primeiros em cada PR e em cada push na `main`; um PR vermelho não deve ser mergeado.

**Observação:** aprovação de um linter estrutural não equivale a homologação operacional, clínica ou de segurança.


> **Adendo operacional (2026-11-10):** consultar
> [`docs/REFINO_POS_AVALIACAO.md`](../REFINO_POS_AVALIACAO.md) antes de
> implementar o fluxo de pacientes, tipo de exame, conciliação ou dashboard;
> a integração e os SLAs ainda precisam ser homologados.
