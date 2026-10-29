# Especificação de Requisitos

> **Sistema:** Serviço de Anatomia Patológica (SAP) — HC-UFPE / SETISD
> **Origem:** `00-validacao-negocio.md` (regras RN-01 a RN-07, atores, pontos de decisão), `01-visao.md` (escopo e objetivos OBJ-01 a OBJ-07) e o *Feedback do fluxo atual do processo*.
> **Escopo de exames:** Histopatológico (HP), Congelação (CO), Imunohistoquímico (IHQ), Citologia Geral (CG) e Cérvico-vaginal (CCV).

## 1. Requisitos Funcionais (RF)

| ID | Título | Descrição | Prioridade |
| :--- | :--- | :--- | :---: |
| RF001 | Autenticação | Login via LDAP/AD do hospital. | Essencial |
| RF002 | Controle de acesso por perfil | Perfis Recepção, Laboratório/Técnicos, Residentes, Validação/Preceptoria e Técnico Administrativo (Chefia do UACAP), cada um com permissões próprias; nenhum perfil altera dados de setores fora da sua alçada. | Essencial |
| RF003 | Dados do AGHU (leitura) | Consultar o AGHU Slave e preencher automaticamente os dados de paciente, solicitação e amostra, sem redigitação e sem cópia manual divergente. | Essencial |
| RF004 | Registro do caso e vínculo | Criar o caso a partir da solicitação do AGHU, com amostras sempre vinculadas à solicitação e aos identificadores de origem. Não permite registro órfão. | Essencial |
| RF005 | Fluxo por tipo de exame | Manter a definição de etapas e transições permitidas para cada tipo de exame (HP, CO, IHQ, CG, CCV), de forma configurável. | Essencial |
| RF006 | Recepção e conferência | Registrar o recebimento da amostra (data, hora e profissional), revisar o cadastro e gerar a etiqueta com o identificador interno. O protocolo físico assinado continua existindo, a pedido do setor. | Essencial |
| RF007 | Pacientes externos: Regulação | Registrar o envio dos dados do paciente externo à Regulação do hospital e o retorno do cadastro, antes de o caso seguir. | Importante |
| RF008 | Macroscopia | Registrar a macroscopia e gerar o laudo macroscópico, que é emitido ao final da etapa e independe do laudo final. | Essencial |
| RF009 | Congelação | Registrar o ciclo reduzido da Congelação (incluindo a análise macroscópica preliminar), o laudo da Congelação e o aviso ao Bloco Cirúrgico. Ao fim, o material volta à Recepção, que recebe no AGHU a solicitação seguinte (HP). | Importante |
| RF010 | Processamento técnico (HP) | Registrar início por Histotécnico ou Preparo manual, inclusão, corte, coloração e montagem. | Essencial |
| RF011 | Processamento técnico citológico (CG/CCV) | Registrar o fluxo condicional: material líquido (centrifugação), presença de fragmento (cell-block, que passa pela bancada do HP e retorna na Coloração) e coloração, montagem e distribuição. | Importante |
| RF012 | Material derivado | Registrar peças, cassetes, blocos e lâminas, todos rastreáveis até o caso de origem, com etapa atual consultável. | Essencial |
| RF013 | Microscopia e pré-laudo | Permitir que Residentes preencham o pré-laudo em tela única após a análise da peça e o enviem à Preceptoria. | Essencial |
| RF014 | Validação, laudo e arquivo | Preceptoria revisa o pré-laudo, registra o diagnóstico e a confirmação do lançamento do laudo no AGHU e conclui o arquivamento do caso. | Essencial |
| RF015 | Encaminhamentos e retornos | Permitir ao responsável pela etapa encaminhar ou retornar o caso entre etapas (ex.: Macroscopia ou Microscopia para Recepção; Microscopia para Macroscopia, Processamento Técnico ou IHQ), com motivo obrigatório, sem reiniciar o processo e sem perder o histórico. | Essencial |
| RF016 | Processamentos adicionais e IHQ | Permitir pedir recorte, coloração especial, revisão da peça e painel ou ampliação de IHQ, sempre vinculados ao caso original. A IHQ é exame complementar e não gera laudo próprio. | Essencial |
| RF017 | Encaminhamento externo | Registrar envio, finalidade, situação e retorno de material enviado à rede externa terceirizada ou ao hospital conveniado (IHQ), com alerta de material não retornado. | Importante |
| RF018 | Exames externos | Para exames externos, permitir indicar a etapa inicial após o recebimento e marcar (check) etapas já realizadas fora do HC. | Importante |
| RF019 | Progressão controlada e status | Só concluir etapa com campos obrigatórios preenchidos; derivar o status do caso das etapas registradas, impedindo "concluído/liberado/arquivado" com pendências. | Essencial |
| RF020 | Inconformidades e rejeições | Registrar divergências, ausência de informação e condicionamento inadequado, com motivo, situação e resolução vinculados ao caso. | Essencial |
| RF021 | Histórico de movimentações | Registrar e exibir, por caso, cada movimentação (etapa, data/hora, responsável) e cada alteração com valor anterior e novo. | Essencial |
| RF022 | Correção após laudo liberado | Reabertura formal de caso/laudo concluído, com justificativa obrigatória, laudo anterior preservado e permissão restrita. Regra exata depende do ponto de decisão 5. | Importante |
| RF023 | Painel de pendências e prazos | Painel em tempo real de casos pendentes, atrasados ou aguardando complemento, por etapa, com alertas conforme prazos de referência (ponto de decisão 2). | Importante |
| RF024 | Indicadores gerenciais | Exibir turnaround time, taxa de cumprimento de prazos, volume de casos, rejeições, automação do preenchimento e rastreabilidade. | Importante |
| RF025 | Procedimentos faturáveis | Registrar de forma estruturada os procedimentos definidos como faturáveis (lista do ponto de decisão 8) e permitir sua consulta consolidada. | Importante |
| RF026 | Substituição na ausência | Permitir delegar temporariamente validação e permissões da Preceptoria ou Chefia a substitutos, com registro da delegação. | Desejável |
| RF027 | Busca de casos | Localizar casos por número da solicitação, paciente, identificador interno, tipo de exame, etapa ou status. | Importante |

### 📌 Legenda de Níveis de Prioridade:
- **Essencial (Alta):** Funcionalidade indispensável para o funcionamento básico da aplicação. Sem ela, o sistema não pode ir para produção (ex: autenticação, cadastros base).
- **Importante (Média):** Funcionalidade que agrega valor significativo ao negócio e melhora o fluxo de trabalho, mas cuja ausência temporária não impede a operação mínima (ex: relatórios, filtros avançados).
- **Desejável (Baixa):** Funcionalidade complementar, melhoria estética ou recurso secundário que pode ser implementado em sprints futuras (ex: temas visuais, atalhos de teclado).

> **Nota sobre prioridades:** o ponto de decisão 1 (tipos de exame da primeira versão) ainda está em aberto. Por ora, HP é tratado como fluxo essencial; Congelação, Citologia e IHQ externa entram como Importante e sobem para Essencial se a Chefia os incluir na primeira entrega.

## 2. Requisitos Não Funcionais (RNF)
| ID | Categoria | Descrição |
| :--- | :--- | :--- |
| RNF001 | Criptografia | Tokens JWT assinados com HS256 e Cookies HttpOnly para Refresh Tokens. |
| RNF002 | LGPD / Auditoria | Trilha de auditoria obrigatória (antes/depois) em tabela `audit_logs` para mutações. |
| RNF003 | Segurança HTTP | Middleware de Security Headers (anti-cache `no-store`, `X-Frame-Options: DENY`, anti-XSS). |
| RNF004 | Governança Segredos | Proibição de hardcode e validação de env vars na inicialização (`src/config.py`). |
| RNF005 | Integração AGHU | Acesso ao AGHU Slave somente leitura; dados do AGHU nunca são alterados pelo SAP, e dados de origem AGHU e dados do SAP ficam claramente separados no modelo. |
| RNF006 | Integridade do histórico | Registros de histórico e auditoria são imutáveis: sem `UPDATE`/`DELETE` pela aplicação; correções geram novo registro preservando o anterior. |
| RNF007 | LGPD / Privacidade | Dados clínicos expostos apenas conforme o perfil; dados sensíveis não aparecem em logs de aplicação nem em mensagens de erro. |
| RNF008 | Desempenho | Consultas de caso e painel respondem em até 3 s no percentil 95 em condições normais de uso (valor proposto, a validar com o SETISD). |
| RNF009 | Disponibilidade | Disponível no horário de funcionamento do setor, com falha na integração com o AGHU Slave sinalizada ao usuário sem corromper registros do SAP (meta a validar com o SETISD). |
| RNF010 | Usabilidade | Formulários padronizados com validação em tempo real, sinalização clara de pendências e telas utilizáveis em desktop de bancada, com no máximo uma tela principal por etapa. |
| RNF011 | Configurabilidade | Fluxos por tipo de exame, prazos de referência, lista de procedimentos faturáveis e regras de retorno ficam em configuração/dados, não em código, pois dependem de decisões da Chefia. |
| RNF012 | Rastreabilidade técnica | Logs estruturados com identificador de requisição e usuário autenticado, e tratamento padronizado de erros (401, 403, 404, 409, 422). |

## 3. Detalhamento SDD (CARE)
Para cada requisito, a implementação deve seguir o padrão:

### [CARE-RF001] Autenticação LDAP
* **Context (Contexto)**: Servidor LDAP configurado e credenciais de serviço disponíveis.
* **Action (Ação)**: Criar middleware de autenticação que consulte o AD.
* **Result (Resultado)**: Token JWT gerado após sucesso; Código 401 em falha.
* **Evaluation (Avaliação)**: Executar `npm test tests/auth.spec.ts` (deve passar com 100% de sucesso).

### [CARE-RF002] Controle de acesso por perfil
* **Context (Contexto)**: Usuário autenticado (RF001) e grupos/perfis do AD mapeados para os 5 perfis do sistema.
* **Action (Ação)**: Criar middleware de autorização (RBAC) que valide perfil e permissão por rota e por etapa do fluxo.
* **Result (Resultado)**: Acesso permitido apenas às ações do perfil; Código 403 ao tentar alterar dados fora da alçada.
* **Evaluation (Avaliação)**: Executar `npm test tests/rbac.spec.ts`: cada perfil só realiza as ações da seção 6 do documento de negócio.

### [CARE-RF003] Dados do AGHU (leitura)
* **Context (Contexto)**: Conexão somente leitura ao AGHU Slave configurada por variável de ambiente.
* **Action (Ação)**: Criar serviço de consulta que busque paciente, solicitação e amostra por número da solicitação e preencha o formulário do caso.
* **Result (Resultado)**: Campos de origem AGHU preenchidos automaticamente e não editáveis; erro claro quando a solicitação não existir ou o AGHU estiver indisponível.
* **Evaluation (Avaliação)**: Executar `npm test tests/aghu.spec.ts` (com AGHU simulado): nenhum comando de escrita é emitido contra o AGHU.

### [CARE-RF004] Registro do caso e vínculo
* **Context (Contexto)**: Solicitação existente no AGHU e usuário com perfil de Recepção.
* **Action (Ação)**: Criar endpoint POST `/api/casos` que gere o caso e suas amostras com chave de vínculo à solicitação e à amostra do AGHU.
* **Result (Resultado)**: Caso persistido com identificador interno único; Código 422 se faltar vínculo; log de auditoria criado.
* **Evaluation (Avaliação)**: Validar contra JSON Schema definido em `04-modelo-dados.md`; teste de que não existe amostra sem solicitação.

### [CARE-RF005] Fluxo por tipo de exame
* **Context (Contexto)**: Diagramas de fluxo da seção 4 deste documento aprovados.
* **Action (Ação)**: Modelar etapas e transições permitidas por tipo de exame como dados configuráveis, com validação a cada mudança de etapa.
* **Result (Resultado)**: Transição fora do fluxo do tipo de exame é rejeitada (Código 409); etapa inicial customizável apenas para exames externos.
* **Evaluation (Avaliação)**: Executar `npm test tests/fluxo.spec.ts`: todas as transições do diagrama passam e as demais falham.

### [CARE-RF006] Recepção e conferência
* **Context (Contexto)**: Caso criado (RF004) e amostra fisicamente recebida.
* **Action (Ação)**: Criar tela e endpoint de recebimento que registrem data/hora e profissional e gerem etiqueta imprimível com o identificador interno.
* **Result (Resultado)**: Etapa Recepção concluída com responsável e horário; dados sensíveis de identificação do exame não editáveis pela Recepção.
* **Evaluation (Avaliação)**: Executar `npm test tests/recepcao.spec.ts`; conferir a etiqueta gerada contra o modelo definido em `05-interfaces.md`.

### [CARE-RF007] Pacientes externos: Regulação
* **Context (Contexto)**: Exame externo chegou e o paciente não possui cadastro no AGHU.
* **Action (Ação)**: Criar registro de "envio à Regulação" com dados enviados, data e responsável, e baixa automática ou manual quando o cadastro aparecer no AGHU.
* **Result (Resultado)**: Caso fica com pendência "aguardando cadastro" até o retorno; sem cadastro, o caso não avança além da Recepção.
* **Evaluation (Avaliação)**: Executar `npm test tests/regulacao.spec.ts`: caso bloqueado até haver cadastro.

### [CARE-RF008] Macroscopia
* **Context (Contexto)**: Caso HP recebido na Recepção.
* **Action (Ação)**: Criar formulário padronizado de macroscopia (descrição, cassetes gerados) e emissão do laudo macroscópico.
* **Result (Resultado)**: Macroscopia concluída somente com campos obrigatórios; laudo macroscópico registrado no caso; cassetes criados como material derivado.
* **Evaluation (Avaliação)**: Executar `npm test tests/macroscopia.spec.ts`: etapa não conclui com campo obrigatório vazio.

### [CARE-RF009] Congelação
* **Context (Contexto)**: Solicitação de Congelação recebida no AGHU; ciclo reduzido por exigir resposta rápida.
* **Action (Ação)**: Criar fluxo reduzido com análise macroscópica preliminar, laudo da Congelação e registro do aviso ao Bloco Cirúrgico; ao final, devolver o material à Recepção para a solicitação seguinte.
* **Result (Resultado)**: Laudo CO registrado; a solicitação de HP recebida em seguida inicia o fluxo do HP após a etapa de Corte. Se Congelação e HP formam um único caso ou dois casos vinculados ainda está em aberto (seção 6).
* **Evaluation (Avaliação)**: Executar `npm test tests/congelacao.spec.ts`: o HP derivado da CO começa em Coloração (após Corte).

### [CARE-RF010] Processamento técnico (HP)
* **Context (Contexto)**: Macroscopia concluída (ou caso externo com etapa inicial definida).
* **Action (Ação)**: Criar registros das etapas Histotécnico/Preparo manual, inclusão, corte, coloração e montagem, com responsável e horário.
* **Result (Resultado)**: Blocos e lâminas criados e rastreáveis; ordem das etapas respeitada.
* **Evaluation (Avaliação)**: Executar `npm test tests/processamento-hp.spec.ts`.

### [CARE-RF011] Processamento técnico citológico (CG/CCV)
* **Context (Contexto)**: Caso de Citologia Geral ou Cérvico-vaginal recebido.
* **Action (Ação)**: Implementar a decisão "é líquido?" e "tem fragmento (cell-block)?", com desvio para a bancada do HP (preparo manual, inclusão, corte, coloração, montagem) e retorno à Coloração na bancada da Citologia.
* **Result (Resultado)**: Caminho percorrido registrado; as três rotas (líquido com fragmento, líquido sem fragmento, sem líquido) terminam em Coloração, Montagem e Distribuição.
* **Evaluation (Avaliação)**: Executar `npm test tests/processamento-citologia.spec.ts` cobrindo as três rotas.

### [CARE-RF012] Material derivado
* **Context (Contexto)**: Caso com amostras registradas.
* **Action (Ação)**: Criar endpoints de peças, cassetes, blocos e lâminas, sempre com chave para o caso de origem e etapa atual.
* **Result (Resultado)**: Qualquer lâmina, bloco ou cassete é consultável com a trajetória até o caso; Código 422 se não houver vínculo.
* **Evaluation (Avaliação)**: Validar contra JSON Schema em `04-modelo-dados.md`; teste de consulta por identificador interno.

### [CARE-RF013] Microscopia e pré-laudo
* **Context (Contexto)**: Lâminas prontas e usuário com perfil de Residente.
* **Action (Ação)**: Criar tela única de pré-laudo, com envio à Preceptoria.
* **Result (Resultado)**: Pré-laudo salvo com autor e horário; caso muda para "aguardando validação".
* **Evaluation (Avaliação)**: Executar `npm test tests/pre-laudo.spec.ts`.

### [CARE-RF014] Validação, laudo e arquivo
* **Context (Contexto)**: Pré-laudo enviado e usuário com perfil de Preceptoria.
* **Action (Ação)**: Criar ação de validar e registrar diagnóstico, registrar a confirmação do lançamento no AGHU e arquivar o caso.
* **Result (Resultado)**: Caso concluído e arquivado somente sem pendências abertas; responsável registrado.
* **Evaluation (Avaliação)**: Executar `npm test tests/validacao.spec.ts`: arquivamento negado com pendência aberta.

### [CARE-RF015] Encaminhamentos e retornos
* **Context (Contexto)**: Caso em etapa com retorno ou encaminhamento permitido pelo fluxo.
* **Action (Ação)**: Criar ação de encaminhar/retornar com motivo obrigatório e destino válido para o tipo de exame (ver tabela da seção 4.3).
* **Result (Resultado)**: Caso muda de etapa sem reiniciar o processo, ajustes feitos e retorno à etapa de origem; histórico preservado.
* **Evaluation (Avaliação)**: Executar `npm test tests/encaminhamentos.spec.ts`: destinos inválidos são rejeitados; motivo é obrigatório.

### [CARE-RF016] Processamentos adicionais e IHQ
* **Context (Contexto)**: Diagnóstico não fechado na Microscopia.
* **Action (Ação)**: Criar pedido de recorte, coloração especial, revisão ou painel/ampliação IHQ, vinculado ao caso, com fila para o Laboratório.
* **Result (Resultado)**: Pedido na fila; resultado devolvido ao mesmo caso; IHQ não gera laudo próprio.
* **Evaluation (Avaliação)**: Executar `npm test tests/adicionais.spec.ts`: não existe pedido sem caso de origem.

### [CARE-RF017] Encaminhamento externo
* **Context (Contexto)**: Material precisa de processamento em rede terceirizada ou hospital conveniado.
* **Action (Ação)**: Criar registro de encaminhamento externo (envio, finalidade, situação, retorno) e alerta de atraso de retorno.
* **Result (Resultado)**: Situação do material consultável; alerta quando passar do prazo de retorno (ponto de decisão 7).
* **Evaluation (Avaliação)**: Executar `npm test tests/externo.spec.ts`.

### [CARE-RF018] Exames externos
* **Context (Contexto)**: Exame externo recebido na Recepção.
* **Action (Ação)**: Permitir escolher a etapa inicial e marcar etapas já realizadas externamente.
* **Result (Resultado)**: Caso começa na etapa escolhida; etapas marcadas como "realizadas externamente" aparecem distintas das realizadas no HC.
* **Evaluation (Avaliação)**: Executar `npm test tests/exame-externo.spec.ts`.

### [CARE-RF019] Progressão controlada e status
* **Context (Contexto)**: Fluxos e campos obrigatórios por etapa definidos (RF005).
* **Action (Ação)**: Calcular o status a partir das etapas registradas e bloquear conclusão com campos obrigatórios vazios ou pendências abertas.
* **Result (Resultado)**: Status nunca contradiz o histórico; tentativa indevida retorna 409/422 com a causa.
* **Evaluation (Avaliação)**: Executar `npm test tests/status.spec.ts`: caso com pendência nunca aparece como concluído.

### [CARE-RF020] Inconformidades e rejeições
* **Context (Contexto)**: Amostra com divergência, informação ausente ou condicionamento inadequado.
* **Action (Ação)**: Criar registro de inconformidade com motivo, situação e resolução.
* **Result (Resultado)**: Inconformidade vinculada ao caso e visível nos indicadores; caso só segue como regular após resolução ou justificativa.
* **Evaluation (Avaliação)**: Executar `npm test tests/inconformidades.spec.ts`.

### [CARE-RF021] Histórico de movimentações
* **Context (Contexto)**: Tabela `audit_logs` e tabela de movimentações disponíveis.
* **Action (Ação)**: Registrar etapa, data/hora, responsável e valores antes/depois a cada mutação; criar tela de linha do tempo do caso.
* **Result (Resultado)**: Trajetória completa reconstruível; nenhum registro é apagado ou sobrescrito.
* **Evaluation (Avaliação)**: Executar `npm test tests/historico.spec.ts`: toda mutação gera registro em `audit_logs`.

### [CARE-RF022] Correção após laudo liberado
* **Context (Contexto)**: Caso concluído e regra de reabertura definida (ponto de decisão 5).
* **Action (Ação)**: Criar ação de reabertura com justificativa obrigatória e permissão restrita.
* **Result (Resultado)**: Caso reaberto com laudo anterior preservado e Chefia avisada.
* **Evaluation (Avaliação)**: Executar `npm test tests/reabertura.spec.ts`.

### [CARE-RF023] Painel de pendências e prazos
* **Context (Contexto)**: Prazos de referência configurados (ponto de decisão 2).
* **Action (Ação)**: Criar consulta e tela de pendências, atrasos e aguardando complemento, por etapa, com alertas.
* **Result (Resultado)**: Painel atualizado a cada consulta; casos atrasados destacados.
* **Evaluation (Avaliação)**: Executar `npm test tests/painel.spec.ts` com massa de dados de casos atrasados.

### [CARE-RF024] Indicadores gerenciais
* **Context (Contexto)**: Movimentações registradas com data/hora.
* **Action (Ação)**: Criar consultas dos 7 KPIs da seção 8 do documento de negócio.
* **Result (Resultado)**: Indicadores calculados por período e tipo de exame, acessíveis à Chefia.
* **Evaluation (Avaliação)**: Executar `npm test tests/kpis.spec.ts`: resultados conferem com massa de dados conhecida.

### [CARE-RF025] Procedimentos faturáveis
* **Context (Contexto)**: Lista de procedimentos faturáveis definida (ponto de decisão 8).
* **Action (Ação)**: Registrar cada procedimento faturável de forma estruturada na etapa em que ocorre e criar consulta consolidada.
* **Result (Resultado)**: Procedimentos realizados listados por caso e período.
* **Evaluation (Avaliação)**: Executar `npm test tests/faturamento.spec.ts`.

### [CARE-RF026] Substituição na ausência
* **Context (Contexto)**: Perfil de Chefia com permissão de delegar.
* **Action (Ação)**: Criar delegação temporária com início, fim e substituto.
* **Result (Resultado)**: Substituto assume permissões apenas no período; delegação auditada.
* **Evaluation (Avaliação)**: Executar `npm test tests/delegacao.spec.ts`: permissão expira ao fim do período.

### [CARE-RF027] Busca de casos
* **Context (Contexto)**: Casos persistidos.
* **Action (Ação)**: Criar endpoint GET `/api/casos` com filtros por solicitação, paciente, identificador interno, tipo, etapa e status.
* **Result (Resultado)**: Lista paginada respeitando o perfil do usuário.
* **Evaluation (Avaliação)**: Executar `npm test tests/busca.spec.ts`.

## 4. Desenho do Fluxo do Processo

Baseado no *Feedback do fluxo atual*. Os cinco exames compartilham a mesma espinha dorsal: **Recepção/Triagem → Macroscopia → Congelação → Processamento Técnico → Imunohistoquímico → Microscopia → Arquivo**, com caminhos diferentes por tipo de exame. "Recepção / Triagem" é o nome da etapa; não confundir com o perfil Residentes.

### 4.1 Fluxo geral

```mermaid
flowchart TD
    A(["Solicitação aceita no AGHU"]) --> B["RECEPÇÃO / TRIAGEM<br/>conferir, registrar recebimento, etiqueta"]
    B --> B1{"Paciente externo<br/>sem cadastro?"}
    B1 -- Sim --> B2["Enviar dados à Regulação<br/>para cadastro"]
    B2 --> B3
    B1 -- Não --> B3{"Inconformidade?"}
    B3 -- Sim --> B4["Registrar rejeição / inconformidade"]
    B4 --> B
    B3 -- Não --> C{"Tipo de exame"}

    C -- "HP" --> D["MACROSCOPIA<br/>gera laudo macroscópico"]
    C -- "CO" --> E["CONGELAÇÃO<br/>análise macroscópica preliminar"]
    C -- "CG / CCV" --> G["PROCESSAMENTO TÉCNICO<br/>citológico (ver 4.2)"]
    C -- "Exame externo" --> X["Definir etapa inicial<br/>+ checks de etapas já feitas"]

    D --> P["PROCESSAMENTO TÉCNICO HP<br/>Histotécnico ou Preparo manual<br/>Inclusão, Corte, Coloração, Montagem"]
    D -. "erro" .-> B

    E --> E1["Laudo da Congelação no AGHU"]
    E1 --> E2["Aciona Bloco Cirúrgico<br/>com a resposta"]
    E2 --> E3["Retorna à Recepção:<br/>solicitação 2 (HP)"]
    E3 --> PC["Processamento HP a partir de<br/>Coloração (após Corte)"]
    PC --> M

    P --> M["MICROSCOPIA<br/>pré-laudo e validação"]
    G --> M

    X -. "qualquer etapa" .-> D
    X -. "qualquer etapa" .-> P
    X -. "qualquer etapa" .-> M

    M --> M1{"Diagnóstico<br/>fechado?"}
    M1 -- Sim --> L["Laudo lançado no AGHU"]
    L --> Z(["ARQUIVO"])
    M1 -- Não --> N{"Encaminhamento"}
    N -- "Revisão da peça (só HP)" --> D
    N -- "Recorte / coloração especial" --> P
    N -- "Painel / ampliação IHQ" --> I["IMUNOHISTOQUÍMICO<br/>exame complementar, sem laudo próprio"]
    N -- "Rede externa terceirizada" --> R["Envio externo<br/>registrar envio e retorno"]
    I --> M
    R --> M
    M -. "erro de cadastro/recepção<br/>(sem reiniciar o processo)" .-> B
    B -. "ajustes feitos:<br/>volta à Microscopia" .-> M
```

### 4.2 Processamento técnico: Citologia (CG e CCV)

```mermaid
flowchart TD
    S(["Citologia: início do processamento"]) --> Q1{"É líquido?"}
    Q1 -- Sim --> F1["Centrifugar"]
    F1 --> Q2{"Tem fragmento<br/>(cell-block)?"}
    Q2 -- Sim --> H["Bancada do Histopatológico<br/>Preparo manual, Inclusão,<br/>Corte, Coloração, Montagem"]
    H --> CB["Retorna à bancada da Citologia"]
    CB --> CL
    Q2 -- Não --> CL["Coloração (bancada da Citologia)"]
    Q1 -- Não --> CL
    CL --> MT["Montagem"]
    MT --> DI["Distribuição"]
    DI --> FIM(["Segue para Microscopia"])
```

### 4.3 Encaminhamentos e retornos permitidos

| Origem | Destino | Motivo / observação | HP | CG/CCV |
| :--- | :--- | :--- | :---: | :---: |
| Macroscopia | Recepção | Erros (lista de erros possíveis a definir com o setor) | ✔ | n/a |
| Microscopia | Recepção | Erros; ajustados, o caso retorna à Microscopia sem reiniciar | ✔ | ✔ |
| Microscopia | Macroscopia | Revisão da peça | ✔ | ✘ |
| Microscopia | Processamento Técnico | Recorte / coloração especial | ✔ | ✔ |
| Microscopia | Imunohistoquímico | Painel / ampliação IHQ | ✔ | ✔ |
| Microscopia | Rede externa terceirizada | Diagnóstico não fechado | ✔ | ✔ |

## 5. Rastreabilidade

### 5.1 Regras de negócio → requisitos
| Regra de negócio | Requisitos funcionais | Requisitos não funcionais |
| :--- | :--- | :--- |
| RN-01 Fonte oficial do AGHU | RF003, RF004 | RNF005 |
| RN-02 Vínculo e rastreabilidade | RF004, RF012, RF016, RF017 | RNF005 |
| RN-03 Progressão controlada e status | RF005, RF019 | RNF011 |
| RN-04 Histórico, autoria e auditoria | RF015, RF021, RF022 | RNF002, RNF006, RNF012 |
| RN-05 Autenticação e controle de acesso | RF001, RF002, RF026 | RNF001, RNF003, RNF004, RNF007 |
| RN-06 Inconformidades e rejeições | RF020 | n/a |
| RN-07 Procedimentos faturáveis | RF025 | n/a |

### 5.2 Objetivos de negócio → requisitos
| Objetivo | Requisitos |
| :--- | :--- |
| OBJ-01 Eliminar redigitação e planilhas | RF003, RF006, RF008, RF010 |
| OBJ-02 Reduzir erros de transposição | RF003, RF019, RNF010 |
| OBJ-03 Saber onde está cada amostra, bloco e lâmina | RF012, RF021, RF027 |
| OBJ-04 Reduzir tempo até o laudo e atrasos | RF023, RF024 |
| OBJ-05 Visibilidade de pendências e inconformidades | RF020, RF023 |
| OBJ-06 Histórico completo e auditoria | RF021, RF022, RNF002, RNF006 |
| OBJ-07 Evitar perda de faturamento | RF025 |

## 6. Pontos em aberto que afetam os requisitos

| Ponto de decisão (doc. 00, seção 9) | Requisitos afetados |
| :--- | :--- |
| 1. Tipos de exame da primeira versão | RF005, RF009, RF011, RF016 (prioridades) |
| 2. Prazos de referência | RF023, RF024 |
| 3. Retorno à fase pré-analítica | RF015 |
| 4. Pedido de processamentos adicionais | RF016 |
| 5. Correção após laudo liberado | RF022 |
| 6. Substituição na ausência | RF026 |
| 7. IHQ em hospital conveniado | RF017 |
| 8. Procedimentos faturáveis | RF025 |
| 9. Transição das planilhas | RF018, RNF011 (e plano de implantação) |

Itens do feedback ainda sem definição:
- Lista de **erros possíveis** em Macroscopia → Recepção e Microscopia → Recepção (RF015).
- Se a **Congelação e o HP** que chega em seguida (duas solicitações separadas no AGHU) formam um único caso ou dois casos vinculados (RF004, RF009).
