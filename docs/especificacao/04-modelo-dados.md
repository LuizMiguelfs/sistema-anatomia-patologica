# 04 — Modelo de dados e persistência

## Fontes de dados

O framework utiliza **dois contextos de persistência independentes**:

| Contexto | Banco | Configuração | Responsabilidade |
|---|---|---|---|
| Aplicação (SAP) | SQLite assíncrono | `APP_DB_URL` (ou `SQLITE_DSN`) | `authorized_users`, `refresh_tokens`, `audit_logs` |
| AGHU | PostgreSQL assíncrono | `POSTGRES_DSN` | Consulta de pacientes e dados da origem, sem escrita em produção |
| Desenvolvimento offline | CSV | `PACIENTE_CSV_PATH` | Simulação do catálogo de pacientes sem AGHU |

O provedor de pacientes é selecionado por `PACIENTE_PROVIDER_TYPE` em `src/config.py`. Não confundir as informações externas do AGHU com as entidades locais do SAP. A API pode expor dados de pacientes sem criar uma tabela local de pacientes.

## Entidades persistidas pela aplicação

- `authorized_users`: identificação, papel, situação ativa e timestamps. Controle de autorização local complementar à autenticação de rede.
- `refresh_tokens`: tokens de renovação, identificação do usuário, expiração, grupos e data de criação. Tratar como dados sensíveis; jamais registrar tokens nos logs.
- `audit_logs`: usuário, categoria, ação, recurso, valores anteriores/novos, origem e timestamp. Registros históricos devem permanecer imutáveis.

O esquema canônico das tabelas locais é definido em `src/models/authorized_user.py`, `src/models/refresh_token.py` e `src/models/audit_log.py` e nas revisões Alembic. Referências a `PRONTUARIO` e `EVOLUCAO` em propostas anteriores eram **modelos conceituais**, não tabelas comprovadamente implementadas neste repositório.

## Migrações

Cadeia linear existente: `df72b10ec0f3` → `8a2efbe37bb6` → `4b1f20261103`. O Alembic deve reportar **um head**. A revisão intermediária foi ajustada para não apagar `refresh_tokens` durante instalações novas. Migrações que já tenham rodado no ambiente de equipe exigem revisão e backup antes de reaplicar ou alterar a versão registrada.

Com banco de teste e backup disponível:

```bash
uv run alembic heads
uv run alembic current
uv run alembic upgrade head
```

O banco AGHU não é migrado pelo Alembic local. Em produção, o usuário de conexão do AGHU deve ter somente permissão `SELECT`.
