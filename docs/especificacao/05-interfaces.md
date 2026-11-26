# 05 — Interfaces e integrações

## Interfaces existentes

| Tela Vue | Rota Vue | Backend | Objetivo |
|---|---|---|---|
| `Login.vue` | `/login` | `src/routers/auth.py` | Login e recuperação de sessão |
| `Home.vue` (Início) | `/` | `GET /api/dashboard/resumo` | Retrato das filas agora (não retiradas, pendentes e urgentes por fase, aguardando o patologista), indicadores do banco local e dicionário de KPIs; o que não é medido vem `null` e aparece como "Não medido" |
| `Solicitacoes.vue` | `/solicitacoes/nao-retirados`, `/solicitacoes/retirados`, `/solicitacoes/arquivados` | `GET /api/solicitacoes`, `POST /api/solicitacoes/{id}/retirar` e `/desfazer-retirada` | Solicitações de Exames: Não retirados (urgentes no topo, mais antigas primeiro) e Retirados (mais recentes primeiro), com filtros por tipo, período e busca por prontuário, código AGHU ou código interno. Só a Recepção marca e desfaz a retirada. Arquivados aparece "em breve" |
| `Fase.vue` + `FormularioFase.vue` + `LinhaDoTempo.vue` | `/fases/macroscopia`, `/fases/congelacao`, `/fases/processamento`, `/fases/ihq`, `/fases/microscopia`, `/fases/revisao-de-lamina` | `/api/fases/...` e `GET /api/auditoria/historico` | Fila de cada fase (urgentes no topo, mais antigas primeiro; concluídas ficam 6 dias para edição) e formulário com Salvar e Concluído. Todos os perfis veem; só o perfil da matriz edita. Embaixo, o histórico da solicitação |
| `Configuracoes.vue` + `TrilhaAuditoria.vue` | `/configuracoes` | `/api/admin/usuarios`, `/api/admin/ad-user-search/{login}`, `/api/admin/auditoria` | Perfil do usuário (todos); gestão de usuários (Chefia); trilha de auditoria com ações em português (Chefia e TI) |

`/pacientes` e `/casos` (telas antigas) levam ao Início. O cabeçalho de todas as telas mostra o nome e o perfil de quem entrou. A documentação interativa dos endpoints fica em `/docs`.

### Solicitações de exame (`/api/solicitacoes`)

| Método e rota | Quem | O que faz |
|---|---|---|
| `GET /api/solicitacoes?situacao=NAO_RETIRADO\|RETIRADO` | Todos | Lista das abas Não retirados e Retirados, com `tipo_exame`, `de`, `ate`, `busca`, `pagina`, `limite` |
| `POST /api/solicitacoes/{id}/retirar` | Recepção | Marca o material como retirado e envia a solicitação à primeira fase do tipo de exame (encerra a Recepção) |
| `POST /api/solicitacoes/{id}/desfazer-retirada` | Recepção | Desfaz enquanto a fase seguinte não registrou nada (409 depois disso) |
| `POST /api/solicitacoes` | Recepção | Abre no SAP a solicitação recebida no AGHU (`{"solicitacao_aghu"}`); tipo de exame e paciente vêm do AGHU |
| `GET /api/solicitacoes/busca` | Todos | Busca com filtros de número AGHU, prontuário, identificador, tipo, etapa e status |
| `GET /api/solicitacoes/{id}` | Todos | Detalhe com amostras e `acoes` (`pode_concluir`, `pode_retornar`, destinos de encaminhamento) para o perfil |
| `GET /api/solicitacoes/{id}/historico` | Todos | Movimentações da solicitação |
| `POST /api/solicitacoes/{id}/encaminhar` | Perfil responsável pela etapa atual | Desvio para outra etapa permitida pelo fluxo (ex.: IHQ pedida na Microscopia), com motivo obrigatório |
| `POST /api/solicitacoes/{id}/retornar` | Perfil responsável pela etapa atual | Devolve à etapa de origem do encaminhamento, com motivo |
| `GET /api/solicitacoes/aghu/solicitacao/{numero}`, `GET /api/solicitacoes/{id}/conferencia-aghu`, `POST /api/solicitacoes/{id}/sincronizar-aghu` | Recepção (conferir e sincronizar) | Pré-visualização do AGHU e conferência dos dados cadastrais, sem editar a fonte (RN-01) |

### Fases do setor (`/api/fases`)

| Método e rota | Quem | O que faz |
|---|---|---|
| `GET /api/fases` | Todos | Definição das fases: rótulo, grupo, perfis que salvam e concluem, campos e prazo de edição |
| `GET /api/fases/{etapa}/fila` | Todos | Fila da fase: pendentes e concluídas ainda editáveis |
| `GET /api/fases/{etapa}/solicitacoes/{id}` | Todos | Formulário da solicitação, com `pode_salvar`, `pode_concluir` e `editavel` por campo para o perfil |
| `PUT /api/fases/{etapa}/solicitacoes/{id}` | Perfis que salvam (matriz) | Salvar: grava o rascunho sem exigir obrigatórios; numa fase concluída há até 6 dias, edita exigindo os obrigatórios |
| `POST /api/fases/{etapa}/solicitacoes/{id}/concluir` | Perfis que concluem (matriz) | Concluído: exige os obrigatórios e envia à próxima fase (ou de volta à fase de origem, se veio por encaminhamento) |

Uma etapa só avança por `retirar` (Recepção) ou pelo `concluir` do formulário (RN-03). Campos que o perfil não edita (ex.: diagnóstico para Residentes) são ignorados no envio. Matriz de perfis: Macroscopia (Residentes); Congelação, Microscopia e Revisão de Lâmina (Residentes e patologista salvam, patologista conclui); Processamento Técnico e IHQ (Laboratório); Chefia visualiza tudo e não edita. Os campos dos formulários estão em `src/helpers/formularios_fase.py` e ainda serão definidos com o setor.

### Painel e histórico

- `GET /api/dashboard/resumo`: `operacional`, `gerencial`, `criterios` (definição de cada número) e `filas` (`RetratoFilas`: não retiradas, urgentes, aguardando o patologista e uma `FilaFase` por fase). Só contagens, sem dados de paciente.
- `GET /api/auditoria/historico?recurso=solicitacao:{id}`: linha do tempo da solicitação para qualquer usuário autenticado, só eventos `NEGOCIO_CLINICO` e sem IP. Inclui os registros antigos gravados como `caso:{id}`.

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

- Cliente HTTP central: `frontend/src/services/api.ts`, com cookies, token bearer e uma única tentativa de renovação após 401. Services de domínio usam esse cliente e têm `.spec.ts` ao lado: `solicitacoes.ts`, `fases.ts`, `auditoria.ts` (rótulos das ações), `historico.ts` (linha do tempo), `painel.ts` (retrato das filas) e `usuarios.ts`.
- Sessão do usuário: `frontend/src/stores/auth.ts` (inclui o rótulo do perfil exibido no cabeçalho). Rotas privadas passam por guarda no `frontend/src/router/index.ts`.
- UI compartilhada: `Button.vue`, `Card.vue`, `DataTable.vue`, `Modal.vue`, `LoadingIndicator.vue`, `FormularioFase.vue`, `LinhaDoTempo.vue` e `TrilhaAuditoria.vue`.
- A integração AGHU/LDAP depende de credenciais e de rede interna. Em desenvolvimento, o AGHU simulado (`AGHU_PROVIDER_TYPE=SIMULADO`, dados fictícios em `data/aghu_simulado.json`) e o login simulado servem só para demonstração e não equivalem à integração real.
- A origem AGHU é somente leitura: o SAP não edita dados de paciente nem da solicitação (RN-01).

## Dependências externas ainda sujeitas a validação

Impressora/etiquetas, leitor de códigos e sincronização de laudos não possuem contratos completos demonstrados nas rotas deste snapshot. Não presumir que estes fluxos estão prontos para demo sem testes de ponta a ponta.

## Matriz inicial das tarefas 04, 05 e 08 (proposta para validação com o HC)

- **Consultar:** os cinco perfis do SAP visualizam filas, fases e histórico segundo a política atual de acesso autenticado. A proteção de dados clínicos por necessidade de acesso ainda exige validação institucional.
- **Retirada e desfazimento:** exigem a própria credencial AD de profissional com perfil local `RECEPCAO`, inclusive se a estação estiver aberta em nome de outra pessoa. A auditoria distingue responsável confirmado e sessão da estação; nenhuma senha é armazenada.
- **Macroscopia:** Residentes salvam e concluem. **Processamento e IHQ:** Laboratório salva e conclui. **Microscopia, Congelação e Revisão:** Residente pode preparar rascunho; Preceptoria valida e conclui. Diagnóstico clínico é campo restrito à Preceptoria.
- **Liberação:** não é o mesmo que conclusão da fase. Em demonstração, a Preceptoria pode registrar um evento **fictício** de liberação do AGHU, identificado como simulação; fora do modo Mock o endpoint é bloqueado. **Arquivar:** somente Preceptoria e somente após liberação registrada.
- **Pendências de validação:** matriz definitiva de acesso a dados clínicos com os profissionais do HC; evento real de laudo liberado no AGHU com SETISD; regras de revisão e retificação após liberação; importação ou referência segura a PDF oficial do AGHU.

A API `GET /api/permissoes` expõe a matriz inicial e as capacidades do perfil. O frontend apenas apresenta os controles; todas as decisões de autorização continuam no servidor.
