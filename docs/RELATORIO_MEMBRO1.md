# SAP HC-UFPE — Entrega Membro 1: autenticação, sessão e perfis

**Base de comparação:** `HCUFPE/Framework-SETISD-HC-UFPE` (branch `master` consultado em 03/11/2026). **Esta entrega é um patch sobre o framework, não um sistema SAP completo.**

## Requisitos atendidos tecnicamente

- **RF001:** login Mock em desenvolvimento e autenticação LDAP/AD em ambiente real; uma falha de credenciais retorna 401. Produção recusa Mock e LDAP não criptografado; Mock exige `AUTH_ALLOW_MOCK=true` e `MOCK_AUTH_PASSWORD` em desenvolvimento; não há senha Mock padrão em runtime.
- **RF002:** perfis locais `RECEPCAO`, `LABORATORIO`, `RESIDENTE`, `PRECEPTORIA`, `CHEFIA`. Depois do AD, exige cadastro local ativo; acesso retorna 403 caso contrário. `require_roles(...)` fornece guarda de backend para cada nova rota/etapa. **A matriz de operações por etapa ainda exige homologação**, portanto não foi inventada.
- **RNF001:** access JWT HS256 de curta duração; refresh aleatório de alta entropia em cookie HttpOnly/SameSite=Lax, `Secure` em produção. SHA-256 do refresh no banco; rotação atômica de uso único. Logout revoga a sessão. "Lembrar" gera cookie persistente; sem marcar, cookie de sessão.
- **RNF002/RNF006:** login, refresh e logout adicionam `audit_logs` sem guardar senhas, JWTs ou valor bruto do refresh. Para mudanças locais de perfil, script de provisionamento adiciona auditoria antes/depois.
- **RNF004/RNF007:** validação centralizada de segredos, sem chave de produção fixa no código; respostas de erro não reproduzem exceções LDAP, credenciais ou dados clínicos.
- **Frontend:** Pinia mantém access JWT somente em memória; restauração da sessão por refresh; interceptor Axios com uma renovação compartilhada em erros 401, impedindo tempestade de refresh; login e menu de perfil vinculados a dados profissionais do próprio usuário na sessão; guard de navegação padrão privado.
- **Testes adicionados:** login válido/inválido, `users/me`, falta de autorização local, refresh hash/rotação/replay, logout, revogação imediata por inativação, mudança de perfil, CSRF básico, tipo de JWT e busca Mock.

## Falhas reais descobertas no framework-base

1. A rota antiga de refresh chamava `authenticate_user(username, None)` — AD não aceita senha ausente.
2. `JWT_SECRET` possuía fallback público e Mock era ativado sem `AD_URL` até mesmo em produção.
3. Perfis locais apareciam na interface, mas eram **dados simulados**, sem persistência no backend. Este patch oferece tabela + CLI segura, **não altera a tela de Configurações simulada**.
4. O access token ficava em `localStorage`, persistindo além da vida da aba.
5. O interceptor Axios não descartava `/api/login`/`/api/token/refresh` de retries, podendo entrar em ciclos ou invalidar sessões.
6. A revisão Alembic `8a2efbe37bb6` do framework apaga a tabela `refresh_tokens`. Não execute migrações em base com dados reais sem revisão do DBA e backup.

## Arquivos

| Área | Arquivos de substituição/adição |
|---|---|
| Backend | `src/auth/auth.py`, `src/models/refresh_token.py`, **novo** `src/models/authorized_user.py`, `src/routers/auth.py`, `src/config.py` |
| Frontend | `frontend/src/stores/auth.ts`, `frontend/src/services/api.ts`, `frontend/src/router/index.ts`, `frontend/src/layouts/LoginLayout.vue`, `frontend/src/views/Login.vue`, `frontend/src/components/ProfileDropdown.vue` |
| Testes | `tests/conftest.py`, `tests/test_auth.py`, `tests/test_auth_ad_search.py` |
| Operação | `scripts/provision_sap_user.py`, `alembic/env.py`, **nova** migração `alembic/versions/4b1f20261103_sap_auth_tables.py`, `docs/ENV_MEMBRO1.exemplo` |

## Validação no Fedora

1. Aplique em **branch própria** com `./APLICAR_FEDORA.sh /caminho/do/repo`. O script recusa árvore suja ou arquivos-base alterados. Não altera a branch principal nem publica sozinho.
2. `cd /caminho/do/repo && uv sync` (o projeto solicita Python >=3.13).
3. Para testes, use `uv run pytest -q tests/test_auth.py tests/test_auth_ad_search.py` com Mock e banco SQLite temporário.
4. `cd frontend && npm ci && npm run build && cd ..`.
5. `uv run python audit_framework.py .` e revise manualmente os resultados.
6. Para produção: revisar os migrations com DBA (histórico legado destrutivo), configurar segredos, TLS, banco, cadastro local de cada usuário e testar LDAP somente na rede autorizada. Não usar dados reais de pacientes em testes.

## Provisionamento local (sem API pública)

No host autorizado, **com backup do SQLite e validação institucional do perfil**:

```bash
uv run python -m scripts.provision_sap_user \
  --username usuario.de.rede --role RECEPCAO --actor operador.autorizado --confirm
```

Outros perfis: `LABORATORIO`, `RESIDENTE`, `PRECEPTORIA`, `CHEFIA`. O script consulta a existência/ativação do usuário no AD via conta de serviço (Mock somente em desenvolvimento). Depois registra autorização e log no DB local. Para retirar o acesso: repita com `--deactivate` e o perfil atual.

**Atenção:** o comando exige execução em host administrado; qualquer operador com escrita no DB poderia executar o script. O mecanismo de autorização/dupla aprovação para provisionar contas é uma decisão de governança ainda pendente.

## Pontos de decisão que não podem ser inventados

1. **Configuração AD real:** domínio, URL LDAPS, certificado/CA, Base DN, conta de serviço e permissões de pesquisa, grupos (inclusive grupos aninhados). `memberOf` obtém grupos **diretos**, não os aninhados; validar com SETISD.
2. **Perfis e operações:** a especificação define os cinco papéis, **não** fornece aqui matriz fechada de endpoints e operações por etapa. É preciso aprovar ações por perfil: criar caso, registrar macro, processar lâmina, pré-laudar, validar, reabrir, consultar logs etc. Frontend nunca substitui a checagem de backend.
3. **Governança do cadastro local:** quem aprova/presta contas por atribuição, revogação, substituição e auditoria de perfis? Não foi adicionado fluxo web administrativo sem definição institucional.
4. **Política de sessão:** esta versão usa 15 min access, 12 h sessão não persistente e 30 dias persistente, valores propostos; a Chefia/segurança pode exigir limites menores, inatividade ou autenticação adicional.
5. **Hospedagem e cookies:** DNS do SAP, HTTPS, proxy reverso, CORS permitido e política de headers Origin. `Secure` é obrigatório em produção; o ambiente local HTTP utiliza `Secure=false`.
6. **Migrações e dados legados:** histórico Alembic existente não é seguro para upgrade direto; a migração nova repara esquema ausente e não reverte destrutivamente. O DBA deve comparar com o banco instalado e definir plano de restauração/revogação de sessões legadas.
7. **Tela de Configurações existente:** a lista de usuários no componente `frontend/src/views/Configuracoes.vue` continua simulada. Não representa autorizações efetivas; necessita tarefa separada para endpoints CRUD auditáveis e controle de quem pode aprovar.

## Critério para homologar

A suíte pytest e o build Vue precisam rodar no checkout real, auditor passar, credenciais de teste do LDAP ser validadas na rede autorizada (usuário ativo, desativado, grupos e conta inexistente), roles aprovadas, migração validada em cópia de banco, e checagem manual de que dados de casos/AGHU respeitam restrições de perfil. **Este patch não comprova isso sozinho.**
