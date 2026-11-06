# SPEC.md - Contrato de Desenvolvimento (SDD)

## 1. Visão Geral e Resultados Esperados
Este documento é a ÚNICA fonte de verdade para a orquestração do desenvolvimento. O objetivo é construir um sistema hospitalar seguro e em conformidade com a LGPD.

### Objetivos de Alto Nível
- [ ] Implementar autenticação via LDAP/AD.
- [ ] Gerenciar cadastro de pacientes (CNS/CPF).
- [ ] Garantir trilhas de auditoria imutáveis.

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
| Testes para cada funcionalidade nova | Backend: `pytest` em `tests/`. Frontend: um `.spec.ts` (Vitest) para cada novo service ou store, ao lado do arquivo (`npm test`). |
| AES-256 para dados sensíveis | AES-256-GCM em `src/helpers/crypto_helper.py`, chave em `SAP_DATA_KEY`. Cifra só o que identifica um único paciente (nome, nome da mãe e do pai, CPF, CNS, data de nascimento e prontuário), nas tabelas do SAP e no antes/depois da auditoria clínica (`CAMPOS_PACIENTE`). Busca exata por esses valores usa índice HMAC (`indice_busca`). |
| Dependências documentadas | Tabela "Dependências externas documentadas" do `06-arquitetura.md`, atualizada no mesmo commit que adiciona a dependência. |
| Sem exclusão física | Nenhum `DELETE` pela aplicação: registros são inativados ou marcados (`deleted_at`, `active`/`ativo`). A trilha `audit_logs` tem triggers que bloqueiam `UPDATE`/`DELETE`. |
| RBAC | Perfil lido do banco local a cada requisição (`auth_handler.decode_token`); rotas restritas com `auth_handler.require_roles(...)`. |

## 4. Task Breakdown (Plano de Implementação)
### Fase 1: Infraestrutura e Dados
- [ ] [TASK-001] Validar esquemas de banco de dados conforme `04-modelo-dados.md`.
- [ ] [TASK-002] Configurar ambiente de auditoria de logs.

### Fase 2: Funcionalidades Essenciais
- [ ] [TASK-003] Implementar Módulo de Autenticação (RF001).
- [ ] [TASK-004] Implementar Cadastro de Pacientes (RF002).

### Divisão de responsabilidade
1. Autenticação, sessão, refresh e papéis: `src/auth`, `src/routers/auth.py`, `frontend/src/stores/auth.ts`.
2. Auditoria, logs, health e administração (inclui gestão de usuários): `src/models/audit_log.py`, `src/routers/admin.py`, `src/routers/usuarios.py`, `src/routers/health.py`, `frontend/src/views/Configuracoes.vue`.
3. Pacientes e múltiplas fontes: `src/providers/*paciente*`, `src/controllers/paciente_controller.py`, `frontend/src/views/Pacientes.vue`.
4. Casos de uso centrais e workflow clínico: módulo de casos (branch `feature/modulo-casos`).
5. Dashboard e agregações: `src/routers/dashboard.py`, `frontend/src/views/Home.vue`.
6. Repositório, conexões, rotas, navegação, SQL compartilhado, migrações, documentação e validação conjunta.

## 5. Critérios de Verificação Global
- [ ] 100% de cobertura em rotas de autenticação.
- [ ] Zero vulnerabilidades críticas no lint de segurança.
- [ ] Conformidade total com os esquemas JSON/OpenAPI.

### Critérios para aceitar a integração
- [x] Rotas Vue reunidas em um único array com guarda de autenticação; páginas de exemplo retiradas.
- [x] Menu com Dashboard, Pacientes e Configurações; rota de histórico de auditoria incluída na API.
- [x] Engines e sessões administradas pelo ciclo de vida do FastAPI.
- [x] `audit_framework.py` executa sem `NameError`.
- [x] Migrações com IDs encadeados em uma única linha e revisão intermediária não destrutiva para instalações novas.
- [ ] `pytest -q` integral em ambiente com dependências instaladas e configurações de teste.
- [ ] `npm ci && npm run build` e navegação testadas no navegador.
- [ ] Migrações executadas e conferidas em cópia de banco real com backup.
- [ ] Integração do módulo 4 e fluxos complementares homologados com os outros membros.
- [ ] Testes reais de LDAP/AGHU, permissões, retenção e privacidade aprovados pela equipe responsável.

## 6. Regras de mudança
Nunca colocar `.env`, tokens, chaves (`JWT_SECRET`, `SAP_DATA_KEY`) ou dados reais de pacientes no Git. Os módulos não devem importar implementações concretas diretamente de outros módulos quando houver interface de Provider. Para SQL dinâmico de usuário, usar bind parameters, não substituição textual. Não apagar logs de auditoria. Revisar migrações com o time antes de aplicá-las em banco já utilizado.

## 7. Validação recomendada

```bash
python audit_framework.py
uv run pytest -q
cd frontend && npm ci && npm test && npm run build
uv run alembic heads
```

**Observação:** aprovação de um linter estrutural não equivale a homologação operacional, clínica ou de segurança.
