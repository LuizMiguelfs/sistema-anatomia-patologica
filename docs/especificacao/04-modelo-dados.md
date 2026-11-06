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

- `authorized_users`: login de rede, nome (vindo do AD na inclusão), perfil, situação ativa e timestamps. Controle de autorização local complementar à autenticação de rede. Gerenciada pela Chefia (RF028); não há exclusão: o acesso é inativado (`active = 0`).
- `refresh_tokens`: hash SHA-256 do token de renovação, identificação do usuário, expiração, metadados (`groups`), data de criação e `deleted_at` (exclusão lógica ao renovar ou sair). Tratar como dados sensíveis; jamais registrar tokens nos logs.
- `audit_logs`: usuário, categoria, ação, recurso, valores anteriores/novos, origem e timestamp. Registros históricos devem permanecer imutáveis. `dados_anteriores` e `dados_novos` são gravados cifrados com AES-256 (`aes256gcm:v1:...`) e decifrados na leitura pela API.

O esquema canônico das tabelas locais é definido em `src/models/authorized_user.py`, `src/models/refresh_token.py` e `src/models/audit_log.py` e nas revisões Alembic. Referências a `PRONTUARIO` e `EVOLUCAO` em propostas anteriores eram **modelos conceituais**, não tabelas comprovadamente implementadas neste repositório.

## Migrações

Cadeia linear existente: `df72b10ec0f3` → `8a2efbe37bb6` → `4b1f20261103` → `c7a1d2e3f405` (triggers de imutabilidade de `audit_logs`) → `d3b8f1a2c6e7` (`refresh_tokens.deleted_at`) → `e5a9c4d7b210` (`authorized_users.nome`). O Alembic deve reportar **um head**. A revisão intermediária foi ajustada para não apagar `refresh_tokens` durante instalações novas. Migrações que já tenham rodado no ambiente de equipe exigem revisão e backup antes de reaplicar ou alterar a versão registrada.

Com banco de teste e backup disponível:

```bash
uv run alembic heads
uv run alembic current
uv run alembic upgrade head
```

O banco AGHU não é migrado pelo Alembic local. Em produção, o usuário de conexão do AGHU deve ter somente permissão `SELECT`.

## Caso (módulo do Membro 4)

- **Caso = solicitação do AGHU.** Cada solicitação gera um caso; não existe caso sem solicitação (RN-02).
- **Congelação (CO) e Histopatológico (HP)** chegam como duas solicitações e geram dois casos.
- **Identificador interno:** `SIGLA-NNNN/AA` (ex.: `HP-0001/26`). `SIGLA` ∈ {HP, CO, IHQ, CG, CCV}; `NNNN` é sequencial **por sigla**, com quatro dígitos, e recomeça em 0001 a cada ano; `AA` são os dois últimos dígitos do ano. O identificador é único.
- Dados de paciente gravados na tabela de casos seguem a regra de AES-256 do `SPEC.md`.

## Regras de Integridade
* Trilha de auditoria obrigatória em `audit_logs` para mutações e proibição de exclusão física de registros de auditoria.
* Nenhuma tabela do SAP sofre exclusão física: usar exclusão lógica (`deleted_at`) ou situação (`active`/`ativo`).
* Dados sensíveis gravados pelo SAP são cifrados com AES-256 (`SPEC.md`).

## Esquemas JSON

### [SCHEMA] Esquema JSON - AuditLog
Formato do registro como entra no helper `registrar_auditoria` e como sai da API (no banco, `dados_anteriores` e `dados_novos` ficam cifrados).
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AuditLog",
  "type": "object",
  "properties": {
    "usuario": { "type": "string" },
    "categoria": { "type": "string", "enum": ["SEGURANCA", "NEGOCIO_CLINICO", "CONFIGURACAO"] },
    "acao": { "type": "string" },
    "recurso": { "type": "string" },
    "dados_anteriores": { "type": ["object", "null"] },
    "dados_novos": { "type": ["object", "null"] },
    "ip_origem": { "type": ["string", "null"] }
  },
  "required": ["usuario", "categoria", "acao", "recurso"]
}
```

### [SCHEMA] Esquema JSON - Paciente
> **Pendente:** o módulo de pacientes (PR #1) aceita CPF opcional e com máscara, o que diverge deste esquema (CPF obrigatório, 11 dígitos). A view do AGHU (`vw_solicitacao`) não traz CPF nem CNS, e sim o prontuário. Decisão em aberto com o setor.
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Paciente",
  "type": "object",
  "properties": {
    "nome": { "type": "string", "minLength": 3 },
    "cpf": { "type": "string", "pattern": "^[0-9]{11}$" },
    "cns": { "type": "string", "pattern": "^[0-9]{15}$" },
    "data_nascimento": { "type": "string", "format": "date" }
  },
  "required": ["nome", "cpf", "data_nascimento"]
}
```

### [SCHEMA] Esquema JSON - Usuário autorizado (saída de `/api/admin/usuarios`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "UsuarioSap",
  "type": "object",
  "properties": {
    "username": { "type": "string" },
    "nome": { "type": ["string", "null"] },
    "perfil": { "type": "string", "enum": ["RECEPCAO", "LABORATORIO", "RESIDENTE", "PRECEPTORIA", "CHEFIA"] },
    "ativo": { "type": "boolean" },
    "criado_em": { "type": "string", "format": "date-time" },
    "atualizado_em": { "type": ["string", "null"], "format": "date-time" }
  },
  "required": ["username", "perfil", "ativo", "criado_em"]
}
```
