# 05 — Interfaces e integrações

## Interfaces existentes

| Tela Vue | Rota Vue | Backend | Objetivo |
|---|---|---|---|
| `Login.vue` | `/login` | `src/routers/auth.py` | Login e recuperação de sessão |
| `Home.vue` | `/` | `GET /api/dashboard/resumo` | Indicadores do painel (podem ser demonstrativos) |
| `Pacientes.vue` | `/pacientes` | `/api/pacientes` | Consulta/cadastro conforme capacidades do provedor |
| `Casos.vue` | `/casos` | `/api/casos` | Abrir caso a partir do AGHU (Recepção), buscar por solicitação, prontuário, identificador, tipo, etapa e status, concluir etapa, encaminhar, retornar e ver histórico |
| `Configuracoes.vue` | `/configuracoes` | `/api/admin/usuarios`, `/api/admin/ad-user-search/{login}`, `/api/admin/auditoria` | Perfil do usuário (todos); gestão de usuários (Chefia); trilha de auditoria (Chefia e TI) |

O backend ainda expõe `GET /api/auditoria/historico`, autenticado, para histórico de um recurso. A documentação interativa de endpoints é fornecida pela aplicação em `/docs`.

### Gestão de usuários (RF028 / UC026)

| Método e rota | Quem | Corpo | Resposta |
|---|---|---|---|
| `GET /api/admin/usuarios` | Chefia | — | Lista de usuários (ativos e inativos) |
| `POST /api/admin/usuarios` | Chefia | `{"username", "perfil"}` | 201 com o usuário; nome obtido do AD. 404 fora do AD; 409 já cadastrado ou grupo do AD ausente |
| `PATCH /api/admin/usuarios/{login}/perfil` | Chefia | `{"perfil"}` | Usuário atualizado. 403 no próprio login; 409 mesmo perfil |
| `PATCH /api/admin/usuarios/{login}/situacao` | Chefia | `{"ativo": true/false}` | Usuário atualizado. 403 no próprio login; 409 sem mudança |
| `GET /api/admin/ad-user-search/{login}` | Chefia e TI (grupo `GLO-SEC-HCPE-SETISD`) | — | `exists`, nome, e-mail e setor do login no AD |

Não existe rota de exclusão de usuário. Perfis aceitos: `RECEPCAO`, `LABORATORIO`, `RESIDENTE`, `PRECEPTORIA`, `CHEFIA`. No front, as chamadas ficam em `frontend/src/services/usuarios.ts`.

## Contrato de integração

- Cliente HTTP central: `frontend/src/services/api.ts`, com cookies, token bearer e uma única tentativa de renovação após 401. Services de domínio (ex.: `services/usuarios.ts`) usam esse cliente e têm `.spec.ts` ao lado.
- Sessão do usuário: `frontend/src/stores/auth.ts`. Rotas privadas passam por guarda no `frontend/src/router/index.ts`.
- UI compartilhada: `Button.vue`, `Card.vue`, `DataTable.vue`, `Modal.vue` e `LoadingIndicator.vue`.
- A integração AGHU/LDAP depende de credenciais e de rede interna; o modo CSV/Mock serve apenas para desenvolvimento, não equivale a integração real.
- Operações de cadastro/edição de pacientes estão sujeitas à configuração do provedor; a origem AGHU deve ser tratada como somente leitura em produção.

## Dependências externas ainda sujeitas a validação

Impressora/etiquetas, leitor de códigos e sincronização de laudos não possuem contratos completos demonstrados nas rotas deste snapshot. Não presumir que estes fluxos estão prontos para demo sem testes de ponta a ponta.
