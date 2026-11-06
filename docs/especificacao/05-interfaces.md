# 05 — Interfaces e integrações

## Interfaces existentes

| Tela Vue | Rota Vue | Backend | Objetivo |
|---|---|---|---|
| `Login.vue` | `/login` | `src/routers/auth.py` | Login e recuperação de sessão |
| `Home.vue` | `/` | `GET /api/dashboard/resumo` | Indicadores do painel (podem ser demonstrativos) |
| `Pacientes.vue` | `/pacientes` | `/api/pacientes` | Consulta/cadastro conforme capacidades do provedor |
| `Configuracoes.vue` | `/configuracoes` | `/api/admin/*` | Administração e auditoria conforme privilégios |

O backend ainda expõe `GET /api/auditoria/historico`, autenticado, para histórico de um recurso. A documentação interativa de endpoints é fornecida pela aplicação em `/docs`.

## Contrato de integração

- Cliente HTTP central: `frontend/src/services/api.ts`, com cookies, token bearer e uma única tentativa de renovação após 401.
- Sessão do usuário: `frontend/src/stores/auth.ts`. Rotas privadas passam por guarda no `frontend/src/router/index.ts`.
- UI compartilhada: `Button.vue`, `Card.vue`, `DataTable.vue`, `Modal.vue` e `LoadingIndicator.vue`.
- A integração AGHU/LDAP depende de credenciais e de rede interna; o modo CSV/Mock serve apenas para desenvolvimento, não equivale a integração real.
- Operações de cadastro/edição de pacientes estão sujeitas à configuração do provedor; a origem AGHU deve ser tratada como somente leitura em produção.

## Dependências externas ainda sujeitas a validação

Impressora/etiquetas, leitor de códigos e sincronização de laudos não possuem contratos completos demonstrados nas rotas deste snapshot. Não presumir que estes fluxos estão prontos para demo sem testes de ponta a ponta.
