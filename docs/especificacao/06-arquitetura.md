# 06 — Arquitetura, implantação e segurança

## Camadas

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

## Segurança e privacidade

JWT e cookies HttpOnly são administrados no módulo de autenticação. Proteção de rotas (autenticação e permissões), RBAC e auditoria devem ser validados com perfis reais da instituição. Não imprimir tokens, senhas, dados clínicos ou DSNs nos logs. Segurança e conformidade LGPD requerem revisão institucional e não podem ser inferidas apenas do auditor estático.

O backend oferece `GET /api/health` para diagnóstico. O painel só deve anunciar indicadores reais quando conectado a fontes reais. `ALLOWED_ORIGINS=*` serve apenas para desenvolvimento; configurar origens explícitas em produção.

## Execução

```bash
cp .env.example .env             # ajustar segredos e provedores com valores locais
uv sync                          # backend
cd frontend && npm ci && npm run build && cd ..
uv run alembic heads
uv run pytest -q
python audit_framework.py
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

**Atenção**: migrações devem ser aplicadas a banco de teste com backup e planejamento de deploy; `src/main.py` ainda usa `create_all` na inicialização. A imagem Docker usa `compose.yaml` e porta 8000. A integração com rede corporativa depende de infraestrutura não embutida no repositório.

## Responsabilidade dos módulos

Autenticação (1), auditoria/admin (2), pacientes (3), fluxo de casos (4), dashboard (5) e integração/infraestrutura/documentação (6). Os módulos 4 e 5 devem informar suas rotas e regras de negócio antes da homologação final.

## Dependências externas documentadas

Toda dependência nova precisa constar nesta lista antes de entrar no projeto (SPEC.md).

| Dependência | Onde | Para quê |
|---|---|---|
| `cryptography` (46.0.3) | backend (`pyproject.toml`) | AES-256-GCM dos dados sensíveis gravados pelo SAP (`src/helpers/crypto_helper.py`). Chave em `SAP_DATA_KEY`. |
| `vitest` (2.1.9) | frontend, só desenvolvimento (`frontend/package.json`) | Testes `.spec.ts` dos services e stores do front (`npm test`). |
