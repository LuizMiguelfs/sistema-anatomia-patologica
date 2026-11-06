# 06 — Arquitetura, implantação e segurança

## 1. Stack Técnica
* Front-end, Back-end e Banco de Dados.
* Front-end: Vue 3, Pinia, Vue Router, Axios e Tailwind (`frontend/`), testado com Vitest.
* Back-end: FastAPI (Python 3.13, `uv`), testado com pytest.
* Banco de Dados: SQLite local da aplicação (Alembic) e AGHU PostgreSQL somente leitura; autenticação no AD/LDAP.

## 2. Conformidade LGPD
* Anonimização e gestão de consentimento (TCLE).
* Dados sensíveis gravados pelo SAP são cifrados com AES-256 (ver "Segurança e privacidade").
* Anonimização e TCLE: forma de aplicação pendente de definição com o SETISD.

## 3. Acessos
* RBAC e MFA.
* RBAC: perfis locais em `authorized_users`, lidos do banco a cada requisição; a Chefia gerencia usuários e perfis (RF028).
* MFA: pendente de definição com o SETISD (o AD atual não oferece segundo fator ao SAP).

## 4. Guardrails para IA (SDD)
Para manter a integridade sistêmica, os assistentes de IA devem aderir às seguintes restrições:

### Escopo Positivo (O que fazer)
- **Documentação de Código**: Comentar funções complexas seguindo o padrão JSDoc/TSDoc.
- **Tratamento de Erros**: Utilizar blocos try-catch com logs de erro padronizados.
- **Testes**: Criar um arquivo de teste `.spec.ts` para cada novo controller ou service.

### Escopo Negativo (O que NÃO fazer - Anti-Patterns)
- **No Hard Deletes**: Proibido o uso de `DELETE` SQL. Utilizar coluna `deleted_at`.
- **No Secrets in Code**: Proibido salvar chaves de API ou senhas no código; utilizar `.env`.
- **No Refactoring Unasked**: Não alterar arquivos de infraestrutura ou configuração global sem instrução explícita no `SPEC.md`.

### Como aplicar no nosso stack
- **JSDoc/TSDoc** no front (`.ts` e `<script setup>`); no backend, docstrings (AGENTS.md).
- **try/except** no backend com log padronizado: ação + tipo da exceção (`logger.error("Falha em %s: %s", acao, erro.__class__.__name__)`), sem dados do registro (RNF007).
- **Testes**: no front, `.spec.ts` (Vitest) para cada novo service ou store; no backend (Python), `pytest` em `tests/` para cada novo controller ou router.
- **Exclusão lógica**: `deleted_at` (ex.: `refresh_tokens`, pacientes CSV) ou situação `active`/`ativo` (usuários, casos).

## 5. Camadas

```text
Vue 3 / Pinia / Vue Router / Axios
           ↓  /api/*
FastAPI (src/main.py, src/routers/)
           ↓
Controllers (src/controllers/)
           ↓
Provider interfaces → implementações CSV/PostgreSQL/SQLite
           ↓
Resources e SQL parametrizado (src/resources/, src/providers/sql/)
```

- `src/main.py`: ciclo de vida, engines de banco, middlewares, rotas e entrega da SPA.
- `src/resources/database.py`: sessões assíncronas e fechamento dos pools. `src/resources/postgres.py`: camada de compatibilidade, sem engine global no import.
- `src/dependencies.py`: seleção/injeção de provedores usados pelos routers.
- `src/helpers/sql_helper.py`: carregamento de SQL da área `providers/sql`; usar parâmetros vinculados `:nome` para valores do usuário. `create_query` é legado e **não deve** receber input da API.
- `alembic/versions`: histórico das migrações do banco *local* da aplicação.

## 6. Segurança e privacidade

JWT e cookies HttpOnly são administrados no módulo de autenticação. Dados sensíveis gravados pelo SAP são cifrados com AES-256-GCM (`src/helpers/crypto_helper.py`); a chave `SAP_DATA_KEY` é obrigatória em todos os ambientes e, se perdida, os dados cifrados não podem ser lidos. Proteção de rotas (autenticação e permissões), RBAC e auditoria devem ser validados com perfis reais da instituição. Não imprimir tokens, senhas, dados clínicos ou DSNs nos logs. Segurança e conformidade LGPD requerem revisão institucional e não podem ser inferidas apenas do auditor estático.

O backend oferece `GET /api/health` para diagnóstico. O painel só deve anunciar indicadores reais quando conectado a fontes reais. `ALLOWED_ORIGINS=*` serve apenas para desenvolvimento; configurar origens explícitas em produção.

## 7. Execução

```bash
cp .env.example .env             # ajustar segredos e provedores com valores locais
uv sync                          # backend
cd frontend && npm ci && npm run build && cd ..
uv run alembic heads
uv run pytest -q
cd frontend && npm test && cd ..
python audit_framework.py
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

**Atenção**: migrações devem ser aplicadas a banco de teste com backup e planejamento de deploy; `src/main.py` ainda usa `create_all` na inicialização. A imagem Docker usa `compose.yaml` e porta 8000. A integração com rede corporativa depende de infraestrutura não embutida no repositório.

## 8. Responsabilidade dos módulos

Autenticação (1), auditoria/admin (2), pacientes (3), fluxo de casos (4), dashboard (5) e integração/infraestrutura/documentação (6). Os módulos 4 e 5 devem informar suas rotas e regras de negócio antes da homologação final.

## 9. Dependências externas documentadas

Toda dependência nova precisa constar nesta lista antes de entrar no projeto (SPEC.md).

| Dependência | Onde | Para quê |
|---|---|---|
| `cryptography` (46.0.3) | backend (`pyproject.toml`) | AES-256-GCM dos dados sensíveis gravados pelo SAP (`src/helpers/crypto_helper.py`). Chave em `SAP_DATA_KEY`. |
| `vitest` (2.1.9) | frontend, só desenvolvimento (`frontend/package.json`) | Testes `.spec.ts` dos services e stores do front (`npm test`). |
