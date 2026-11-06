# SPEC — Contrato de integração do framework SETISD/HC-UFPE

## Fonte de verdade

Os critérios de negócio estão em [02-requisitos](02-requisitos.md) e [03-casos-uso](03-casos-uso.md). O modelo de dados, as interfaces e a implantação estão descritos em [04-modelo-dados](04-modelo-dados.md), [05-interfaces](05-interfaces.md) e [06-arquitetura](06-arquitetura.md). Este arquivo **não substitui** requisitos clínicos e regras institucionais.

## Divisão de responsabilidade

1. Autenticação, sessão, refresh e papéis: `src/auth`, `src/routers/auth.py`, `frontend/src/stores/auth.ts`.
2. Auditoria, logs, health e administração: `src/models/audit_log.py`, `src/routers/admin.py`, `src/routers/health.py`.
3. Pacientes e múltiplas fontes: `src/providers/*paciente*`, `src/controllers/paciente_controller.py`, `frontend/src/views/Pacientes.vue`.
4. Casos de uso centrais e workflow clínico: implementação/integração dependente do módulo do membro 4.
5. Dashboard e agregações: `src/routers/dashboard.py`, `frontend/src/views/Home.vue`.
6. Repositório, conexões, rotas, navegação, SQL compartilhado, migrações, documentação e validação conjunta.

## Critérios para aceitar a integração

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

## Regras de mudança

Nunca colocar `.env`, tokens ou dados reais de pacientes no Git. Os módulos não devem importar implementações concretas diretamente de outros módulos quando houver interface de Provider. Para SQL dinâmico de usuário, usar bind parameters, não substituição textual. Não apagar logs de auditoria. Revisar migrações com o time antes de aplicá-las em banco já utilizado.

## Validação recomendada

```bash
python audit_framework.py
uv run pytest -q
cd frontend && npm ci && npm run build
uv run alembic heads
```

**Observação:** aprovação de um linter estrutural não equivale a homologação operacional, clínica ou de segurança.
