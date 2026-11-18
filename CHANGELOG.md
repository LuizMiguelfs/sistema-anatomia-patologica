# Registro de alterações — pacote de refino

## 2026-11-18 — v1.2.0 — Solicitação de exame em todo o sistema, histórico, painel das filas e CI

- **Termo único:** "caso" passa a "solicitação de exame" no código, nas rotas e no banco. A migração `20261118_renomear_solicitacao` só renomeia tabelas, colunas e índices (sem perda de dados) e descarta as tabelas novas vazias que o sistema cria ao subir antes de migrar. `/api/casos` passa a `/api/solicitacoes` (busca em `/api/solicitacoes/busca`). Na trilha de auditoria, os registros novos usam `solicitacao:<id>` e os antigos (`caso:<id>`) continuam aparecendo no histórico.
- **Avanço só com formulário (RN-03):** sai a rota `concluir-etapa`, que avançava a etapa sem os campos obrigatórios. Uma etapa só avança pela retirada (Recepção) ou pelo Concluído do formulário da fase.
- **Histórico da solicitação:** o formulário de cada fase mostra o que foi feito, por quem e quando, para todos os perfis.
- **Trilha de auditoria em português:** toda ação aparece com rótulo legível em Configurações; o filtro de ação vira lista.
- **Perfil no cabeçalho:** todas as telas mostram o nome e o perfil de quem entrou.
- **Início:** retrato das filas (não retiradas, pendentes e urgentes por fase, aguardando o patologista), com cada número levando à aba certa. "Aguardando complementação" passa a contar as encaminhadas que ainda não voltaram; "Inconformidades abertas" volta a "Não medido", pois o SAP ainda não registra inconformidades.
- **Telas antigas removidas:** Pacientes e Casos saem do frontend; `/pacientes` e `/casos` levam ao Início.
- **Qualidade:** teste da matriz de perfis pela API, testes de componente do formulário da fase (`@vue/test-utils` e `jsdom`, só desenvolvimento) e CI no GitHub Actions (testes, build e auditor em cada PR).
- **Documentação:** especificação (`01`, `04`, `05`, `07`, `SPEC.md`) e README atualizados com o MVP.
- Pendentes: formulários reais de cada fase (após a reunião com o setor), aba Arquivados, deploy de demonstração (aguardando aprovação).

## 2026-11-11 — v1.1.0 — MVP: Solicitações de Exames e fases do setor

- Menu reorganizado: Solicitações de Exames (Não retirados, Retirados, Arquivados em breve), Fase Pré-Analítica (Macroscopia, Congelação, Processamento Técnico, IHQ) e Fase Analítica (Microscopia, Revisão de Lâmina). Pacientes e Casos saem do menu.
- Solicitações: urgentes no topo (Congelação é sempre urgente), filtros por tipo, período e busca por prontuário, código AGHU ou código interno; só a Recepção marca ou desfaz a retirada, com confirmação e auditoria.
- Fases: fila só com o que está na fase, urgentes no topo e mais antigos primeiro; formulário com Salvar (sem obrigatórios) e Concluído (obrigatórios + confirmação); concluídas ficam 6 dias na lista para edição.
- Matriz de perfis: Macroscopia (Residentes), Congelação/Microscopia/Revisão (Residentes preenchem, patologista conclui), Processamento e IHQ (Laboratório), Chefia só visualiza.
- Formulários provisórios em `src/helpers/formularios_fase.py`, a ajustar após a reunião com o setor.
- AGHU simulado (`AGHU_PROVIDER_TYPE=SIMULADO`, dados fictícios em `data/aghu_simulado.json`) e carga de demonstração `python -m scripts.seed_mvp --confirm`.
- Login simulado aceita usuários de demonstração listados em `MOCK_AUTH_USERS` (somente desenvolvimento).
- Migração `20261111_mvp_fases` (retirada, urgência, `caso_fases`, fluxos IHQ e RL).

## 2026-11-10 — Preparação para homologação (sem tag de produção)

- Dashboard conectado aos dados locais, com definição de cada KPI e SLAs parametrizados.
- Cadastro de pacientes read-only, com backend sem operações de escrita no AGHU.
- Criação de casos com exame definido exclusivamente pelo AGHU, sem entrada manual.
- Conciliação cadastral sob demanda com transação única, trilha de auditoria e tratamento de conflitos.
- Migração `20261110_refino_aghu`, novos testes de API e documentação de homologação.
- Testes locais: 110 aprovados, 6 ignorados; `npm run build` e 11/11 pilares do auditor aprovados.
- **Pendente antes de produção:** mapeamento real do exame e das regras de SLA; integração e segurança institucional.
