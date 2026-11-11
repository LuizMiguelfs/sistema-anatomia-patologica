# Registro de alterações — pacote de refino

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
