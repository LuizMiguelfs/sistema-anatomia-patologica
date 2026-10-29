# Serviço de Anatomia Patológica (SAP) — Documento de Validação e Especificação de Negócio

> **Padrão Oficial SETISD / HC-UFPE (HU Brasil) — Fase 0 (Alinhamento de Negócio)**  
> **Público-alvo:** Profissionais das áreas envolvidas e Equipe de TI.  
> **Objetivo:** Descrever o processo de trabalho em **linguagem pura de negócio** (sem jargões técnicos de programação ou banco de dados) para validação, alinhamento de expectativas e tomada de decisão antes de qualquer codificação.

---

## 1. Identificação do Projeto e Contexto Institucional

| Campo                              | Descrição                            |
| :--------------------------------- | :----------------------------------- |
| **Nome do Sistema**                | Serviço de Anatomia Patológica (SAP) |
| **Área Solicitante / Cliente**     | Setor de Anatomia Patológica         |
| **Instância Superior Competente**  | SETISD                               |
| **Líder Técnico (SETISD)**         | Daniel Turmina                       |
| **Objetivo Estratégico HU Brasil** | Emissão de diagnóstico               |

---

## 2. O Problema que Queremos Resolver

> **Objetivo:** Dizer com clareza qual é o problema real de trabalho. Sem rodeios: o que hoje está quebrado, ineficiente ou gerando risco para o hospital?

* **A Dor Central:**  
  *Preenchimento massivo de informações de entrada manual, feitas em planilhas, com alta probabilidade de erros. Ademais, há dificuldade de acesso e descentralização das informações encontradas no AGHU.*

* **Por que isso não pode continuar (Impactos Reais):**
  - **Sobrecarga de Trabalho:** As chefias e equipes perdem horas redigitando dados e conferindo manualmente tarefas que poderiam ser automáticas.
  - **Falta de Visibilidade:** A gestão não sabe em tempo real quem já entregou, quem está com pendências e onde estão os gargalos.
  - **Risco Institucional e Legal:** Lacunas no histórico dos dados sobre os exames realizados no setor.

---

## 3. Como o Processo Funciona Hoje (A Rotina Atual)

> **Objetivo:** Mapear a realidade crua de como as equipes se viram no dia a dia para realizar essa tarefa hoje.

* **Meios Utilizados Hoje:**  
  O AGHU, onde é feito o recebimento dos exames e a entrega dos diagnósticos. A planilha no Teams, que protocola manualmente todo o processo dos diferentes tipos de exames. O WhatsApp, para comunicação interna ágil.

* **Tipos de Exame do Setor:**  
  Histopatológico (HP), Congelação (CO), Imunohistoquímico (IHQ), Citologia Geral (CG) e Cérvico-vaginal (CCV). O Imunohistoquímico é o único que não gera laudo por si só: ele complementa um exame em curso e pode participar do fechamento do diagnóstico.

* **A Rotina Prática de Trabalho:**
  1. **Início:** No AGHU, é aceita a solicitação do exame. Há um grande panorama geral na anatomia patológica que se inicia no recebimento do material para análise. A depender do exame realizado, o processo inicia em fases diferentes, mas semelhantes entre si. Em todos, assim que chegam ao setor, os exames são cadastrados na planilha do Teams. Há uma planilha para cada tipo de exame.
  2. **Fase Pré-Analítica:** Para sair da recepção, deve ser assinado o protocolo físico, com data e nome do profissional que recebeu as amostras. Na planilha, cada informação subsequente, proveniente da fase pré-analítica, é anotada em campos específicos. Em determinados exames, como o histopatológico, são gerados relatórios dessas fases. A macroscopia, por exemplo, gera um laudo próprio ao seu final, além do laudo final emitido após a microscopia.
  3. **Fase Analítica:** Receber os relatórios e a análise da peça dos residentes e da preceptoria, na tentativa de fechar o diagnóstico. Na impossibilidade de fechar o diagnóstico, o caso volta à fase pré-analítica (revisão da peça, recorte ou coloração especial, painel ou ampliação de IHQ) ou é enviado para a rede externa terceirizada.
  4. **Fase Pós-Analítica:** Lançar o laudo no AGHU e arquivá-lo.

---

## 4. O Que a Nova Solução Deve Entregar (Resultado Esperado)

> **Objetivo:** Definir com clareza o que a solução digital deve trazer para eliminar a dor do processo atual.

* **A Proposta de Valor:** *Centralizar o acompanhamento das solicitações e amostras em um único ambiente digital integrado ao AGHU Slave, reaproveitando automaticamente os dados já disponíveis no AGHU e permitindo o registro estruturado das informações específicas do fluxo da Anatomia Patológica. A solução deve possibilitar acompanhar cada caso ao longo das diferentes etapas do processo, desde a recepção da amostra até o processamento, análise, liberação do laudo e arquivamento, reduzindo a dependência de planilhas paralelas e consultas manuais em diferentes telas, considerando os diferentes caminhos que podem ser tomados a depender do exame.*

* **Ganhos Práticos Imediatos:**
  - Visualização centralizada das informações essenciais da solicitação e da amostra, evitando a necessidade de navegar por diferentes telas do AGHU para localizar dados.
  - Preenchimento automático dos dados já disponíveis no AGHU Slave, reduzindo redigitação e possíveis inconsistências.
  - Registro estruturado das informações produzidas dentro do SAP e que não estão contempladas adequadamente no AGHU.
  - Rastreabilidade do caso ao longo das etapas do fluxo, permitindo identificar em que estágio se encontram amostras, blocos, lâminas e demais materiais relacionados.
  - Redução da dependência de controles manuais e planilhas paralelas.
  - Padronização dos registros de processamento, como macroscopia, blocos, cassetes, cortes, colorações, IHQ, revisões e demais procedimentos.
  - Identificação e sinalização de pendências, inconformidades ou informações ausentes durante o processo.
  - Histórico das movimentações e alterações realizadas em cada caso, com registro de etapa, responsável e data.
  - Maior facilidade para localizar casos pendentes, atrasados ou que necessitam de processamento complementar.
  - Apoio ao acompanhamento de materiais enviados para processamento externo, como casos de IHQ realizados em hospital conveniado.
  - Consolidação de informações que possam apoiar o faturamento e reduzir o risco de procedimentos realizados não serem devidamente registrados.
  - Disponibilização de informações gerenciais sobre volume de casos, etapas do fluxo, pendências, rejeições e tempos de processamento.

---

## 5. Como Será o Trabalho no Novo Sistema (O Novo Fluxo)

> **Objetivo:** Explicar em linguagem direta como o usuário vai interagir com o sistema, resolvendo a dor do processo manual de ponta a ponta.

* **1. Os dados já vêm prontos:** O usuário não precisa mais digitar dados do paciente ou da solicitação do zero, nem pular de tela em tela no AGHU para juntar informações. Ao abrir o sistema, os dados essenciais da amostra e da solicitação já vêm preenchidos automaticamente do AGHU Slave. Isso elimina a redigitação, evita inconsistências e centraliza tudo em uma única visualização.
* **2. Preenchimento rápido com travas contra erros:** O registro das etapas que não existem no AGHU (como macroscopia, blocos, cassetes, cortes, colorações, IHQ e revisões) é feito direto em formulários padronizados no novo ambiente. O sistema identifica e sinaliza ativamente qualquer pendência, inconformidade ou informação ausente, reduzindo a dependência de controles em papel e de planilhas paralelas.
* **3. Cada movimentação fica registrada:** A cada avanço do material, da recepção ao arquivamento, o sistema registra automaticamente a etapa, a data, a hora e o responsável pela movimentação. Com isso, saber exatamente onde está uma amostra, um bloco ou uma lâmina (inclusive materiais enviados para processamento externo, como IHQ conveniada) vira uma simples consulta na tela, amparada por um histórico de auditoria completo. A pedido do setor, a Ficha de Trabalho impressa e o protocolo físico de recebimento continuam existindo ao lado desse registro.
* **4. Informação pronta e disponível:** A equipe e a gestão visualizam em painéis atualizados o que está pendente, atrasado ou precisando de complemento. Além de facilitar a rotina de quem está na bancada, o sistema consolida o volume de casos, rejeições e tempos de processamento, reduzindo o risco de que algum procedimento realizado deixe de ser faturado por falta de registro.
* **5. Exames externos com ponto de partida flexível:** Exames externos podem chegar ao HC em diferentes níveis de evolução. Para eles, o sistema permite indicar por qual etapa o exame começa depois de recebido e marcar as etapas que já foram realizadas fora do HC.

---

## 6. Quem Participa do Processo (Atores: Como Faz Hoje vs. Como Fará no Sistema)

| Ator / Perfil no Hospital   | O que faz HOJE (Rotina Manual)                                                                                                                | O que passará a fazer no NOVO SISTEMA                                                                                                     | O que NÃO poderá fazer                                                    |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------ |
| **Recepção**                | Cadastrar manualmente as amostras recebidas na planilha e anexar o identificador interno em cada peça.                                        | Revisão de cadastramento das amostras e anexo da etiqueta com identificador interno impresso em cada peça.                                | Alterar dados sensíveis de identificação do exame.                        |
| **Laboratório / Técnicos**  | Criam relatório impresso e planilha do Teams, correndo risco de esquecer dados ou duplicar lançamentos. Realizam fase pré-analítica.          | Lançam os dados direto no sistema com validações em tempo real e encaminham relatórios pré-processados para conferência da chefia.        | Alterar dados de setores que não sejam de sua alçada.                     |
| **Residentes**              | Preenchimento de pré-laudo após análise da peça no AGHU e Teams.                                                                              | Preenchem em uma tela única o pré-laudo após análise, pronto para ser enviado ao preceptor.                                               | Alterar dados de setores que não sejam de sua alçada.                     |
| **Validação / Preceptoria** | Revisar o pré-laudo e escrever o diagnóstico, enviando os resultados pelo AGHU. Pode solicitar processamentos adicionais ao laboratório.      | Revisar o pré-laudo e escrever o diagnóstico, enviando os resultados pelo AGHU. Pode solicitar processamentos adicionais direto do sistema, que ficam vinculados ao caso. | Alterar dados de setores que não sejam de sua alçada.                     |
| **Técnico Administrativo (Chefia do UACAP)** | Acompanhar o andamento do setor sem uma visão consolidada, dependendo de planilhas e de informações repassadas pelas equipes.                 | Acompanhar painéis de pendências, atrasos, rejeições, volume de casos e tempos de processamento, e responder pelas decisões da seção 9.   | Apagar ou sobrescrever o histórico de registros feitos pelas equipes.     |

> **Nota sobre nomes:** "Recepção / Triagem" é o nome da primeira **etapa** do fluxo. O perfil de quem faz o pré-laudo chama-se apenas **Residentes**, para não confundir os dois.

**Outros participantes do processo:**
- **Regulação do hospital:** cadastra no AGHU os pacientes de exames externos, a partir dos dados enviados pela Anatomia Patológica.
- **Bloco Cirúrgico:** solicita exames no AGHU, envia peças e líquidos ao setor e recebe da equipe a resposta da Congelação.

A forma como esses dois participantes vão interagir com o SAP ainda não foi definida.

---

## 7. Regras de Negócio Inegociáveis (RNs)

> Sete regras que o sistema deve cumprir sempre. Elas reúnem, sem perder conteúdo, as 14 regras da versão anterior.

- **RN-01 (Fonte Oficial do AGHU e Separação dos Dados):** as informações já disponíveis no AGHU devem ser obtidas automaticamente por meio da base institucional disponibilizada pelo HC-UFPE, evitando a redigitação desnecessária de dados clínicos e administrativos. O sistema não deve manter cópias manuais divergentes dessas informações quando a fonte oficial estiver disponível. Os dados originados no AGHU são tratados como dados da fonte institucional; os dados gerados durante o processamento da Anatomia Patológica são armazenados e mantidos pelo SAP. O sistema deve deixar clara essa distinção e manter a vinculação entre ambos.
- **RN-02 (Vínculo e Rastreabilidade de Amostras e Materiais):** toda amostra processada deve estar obrigatoriamente vinculada à solicitação e aos identificadores correspondentes no AGHU; o sistema não deve permitir a criação ou o processamento de registros sem que seja possível determinar, sem possibilidade de erro, a qual solicitação e amostra eles pertencem. Os materiais derivados (peças, cassetes, blocos, lâminas e outros) devem permanecer rastreáveis até o caso de origem durante todo o processo. Procedimentos complementares (recortes, novas colorações, IHQ, revisão) e encaminhamentos externos devem permanecer associados ao caso original e não podem gerar registros isolados. Nos encaminhamentos externos, devem constar envio, finalidade, situação e retorno do material ou resultado.
- **RN-03 (Progressão Controlada do Fluxo e Status Confiável):** uma etapa só pode ser registrada como concluída quando as informações obrigatórias tiverem sido preenchidas; pendências, inconformidades ou ausência de dados essenciais devem impedir ou sinalizar o avanço indevido do caso, evitando retrabalho. O status exibido deve ser derivado ou validado a partir das etapas efetivamente registradas: um caso não pode aparecer como concluído, liberado ou arquivado enquanto existirem etapas obrigatórias ou pendências incompatíveis com esse estado (por exemplo: informação crítica não preenchida, etapa ignorada ou alteração pendente).
- **RN-04 (Histórico, Autoria e Auditoria):** registros anteriores não devem ser apagados nem sobrescritos de forma a eliminar o histórico do caso; toda alteração relevante preserva a informação anterior e a nova, permitindo reconstruir a trajetória do material e das decisões. Toda ação relevante deve estar associada ao usuário autenticado, com data/hora, ação executada e recurso afetado, e a etapa executada ou concluída deve identificar o profissional responsável. As alterações de dados clínicos ou operacionais devem ter trilha de auditoria conforme o padrão institucional do HC-UFPE, informado pelo líder técnico do SETISD (Daniel Turmina).
- **RN-05 (Autenticação Institucional e Controle de Acesso):** o acesso ao sistema deve ocorrer por autenticação institucional, utilizando os mecanismos previstos pelo framework do HC-UFPE disponível no repositório. As funcionalidades de cada usuário devem respeitar os perfis e permissões definidos pelo controle de acesso institucional.
- **RN-06 (Registro de Inconformidades e Rejeições):** amostras com divergências, ausência de informações, condicionamento inadequado ou outras inconformidades não podem ser tratadas como casos regulares sem que a ocorrência seja registrada. O sistema deve manter o motivo, a situação e a resolução da inconformidade vinculados ao caso.
- **RN-07 (Registro de Procedimentos Relevantes ao Faturamento):** procedimentos realizados ao longo do fluxo que tenham impacto administrativo ou de faturamento devem ser registrados de forma estruturada, evitando que sua contabilização dependa exclusivamente de anotações manuais ou controles paralelos.

---

## 8. Painel de Gestão e Indicadores Estratégicos (KPIs)

| Indicador | O que mede |
| :--- | :--- |
| **Turnaround time** | Tempo total entre a recepção da amostra e a emissão do laudo conclusivo. |
| **Erro de transposição** | Divergências entre o dado de origem e o dado registrado. |
| **Taxa de cumprimento de prazos** | Proporção de casos concluídos dentro do prazo de referência de cada tipo de exame. |
| **Mapa de pendências e atrasos** | Casos pendentes, atrasados ou aguardando processamento complementar, por etapa. |
| **Automação do preenchimento** | Proporção de dados que chegam do AGHU sem digitação manual. |
| **Rastreabilidade (status das amostras)** | Etapa atual de cada amostra, bloco e lâmina. |
| **Monitoramento de inconsistências** | Inconformidades e rejeições registradas, com motivo e situação de resolução. |

---

## 9. Matriz de Pontos de Decisão (Chefia do UACAP / Gestão do Negócio)

> **Como ler esta matriz:** cada linha é uma pergunta que o sistema não consegue responder sozinho e que a equipe de TI não deve decidir no lugar do hospital. A coluna "Por que precisa ser decidido" explica o que muda no sistema conforme a resposta; "Opções em discussão" traz caminhos possíveis para facilitar a conversa, e não decisões já tomadas. Quando houver resposta, o status muda para 🟢 Decidido, com a data e a definição registradas na própria linha.

| # | Ponto a decidir | Por que precisa ser decidido (o que muda no sistema) | Opções em discussão | Quem deve decidir? | Status / Definição |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Tipos de exame da primeira versão:** quais tipos de exame entram na primeira entrega do sistema? | Hoje há uma planilha por tipo de exame e cada tipo começa em uma fase diferente. O sistema precisa de um fluxo para cada tipo, então quanto mais tipos na primeira versão, maior e mais demorada a entrega. | Começar por um ou dois tipos (por exemplo, histopatológico) e ampliar depois; ou entregar todos os tipos de uma vez. | Chefia do UACAP | 🟡 Em definição |
| **2** | **Prazos de referência:** qual o prazo esperado para cada tipo de exame (e, se necessário, para cada etapa)? | Define o que o sistema considera "atrasado", quando dispara alertas e como é calculada a taxa de cumprimento de prazos. Sem prazo definido, o painel não consegue apontar atrasos. | Um prazo único para todos os exames; um prazo por tipo de exame; prazos por etapa do fluxo. | Chefia do UACAP, com Preceptoria | 🟡 Em definição |
| **3** | **Retorno à fase pré-analítica:** quando o diagnóstico não fecha, quem decide que o caso volta e o que precisa ser informado? | O sistema precisa saber se o retorno exige motivo obrigatório e quem pode pedi-lo. O caso volta a uma etapa anterior sem apagar o histórico do que já foi feito (RN-04). | O profissional responsável pela etapa em que o caso está define o encaminhamento ou retorno (é o que diz o feedback do fluxo atual; falta confirmar quem é esse responsável na Microscopia); apenas a Preceptoria pode devolver o caso, com motivo obrigatório; ou Residentes também podem sugerir o retorno, com confirmação da Preceptoria. | Preceptoria e Chefia do UACAP | 🟡 Em definição |
| **4** | **Pedido de processamentos adicionais:** o que a Preceptoria pode pedir pelo sistema (novos cortes, colorações, IHQ, revisão), para quem o pedido vai e se precisa de aprovação? | Define o formulário de pedido, quem recebe o aviso e se o pedido entra direto na fila do laboratório. Todo pedido fica vinculado ao caso original (RN-02). | Pedido direto da Preceptoria para o Laboratório; ou pedido com aprovação prévia da Chefia. | Preceptoria e Chefia do UACAP | 🟡 Em definição |
| **5** | **Correção após laudo liberado:** qual o rito para corrigir ou reabrir um laudo ou dado já concluído? | Define se haverá reabertura formal, com justificativa gravada e laudo anterior preservado (RN-04), e quem tem permissão para fazê-la. Também precisa considerar que o laudo já foi lançado no AGHU. | Reabertura apenas pela Chefia, com justificativa obrigatória; ou pelo Preceptor responsável, com justificativa e aviso à Chefia. | Chefia do UACAP, com apoio do SETISD no que envolver o AGHU | 🟡 Em definição |
| **6** | **Substituição na ausência:** quem valida o laudo e responde pelas decisões quando o preceptor ou a chefia titular estiver de férias ou afastado? | Evita que casos fiquem parados por ausência de uma única pessoa. Define quem recebe as permissões de validação temporariamente. | Lista fixa de substitutos cadastrados; ou delegação temporária registrada pela própria Chefia. | Chefia do UACAP | 🟡 Em definição |
| **7** | **IHQ em hospital conveniado:** o que deve ser registrado no envio e no retorno do material, e quem confirma o recebimento? | Define os campos do encaminhamento externo (envio, finalidade, situação e retorno, conforme RN-02), o prazo esperado de retorno e o alerta para material que não voltou. | Registro feito pelo Laboratório no envio e no retorno; ou envio pelo Laboratório e confirmação de retorno pela Preceptoria. | Chefia do UACAP e Laboratório | 🟡 Em definição |
| **8** | **Procedimentos que contam para o faturamento:** quais procedimentos realizados no fluxo têm impacto no faturamento? | O sistema só consegue registrar de forma estruturada (RN-07) o que estiver numa lista definida. Sem essa lista, o risco de procedimento não faturado continua. | Lista fornecida pela Chefia, validada com a área de faturamento do hospital. | Chefia do UACAP, com a área de faturamento do HC-UFPE | 🟡 Em definição |
| **9** | **Transição das planilhas:** por quanto tempo planilhas e sistema funcionam em paralelo, e o que acontece com o histórico das planilhas do Teams? | Define a data de início do uso oficial do SAP, se o histórico antigo será levado para o sistema ou apenas consultado nas planilhas, e quando as planilhas deixam de ser atualizadas. | Período curto de uso paralelo com data de corte; ou virada direta por tipo de exame. Histórico: migrar, ou manter planilhas apenas para consulta. | Chefia do UACAP e SETISD | 🟡 Em definição |

---
---

# 📘 GUIA METODOLÓGICO: COMO ESTE DOCUMENTO SE INTERLIGA AOS DEMAIS ARQUIVOS DO PROJETO

> **Apresentação Executiva para a Chefia:**  
> Esta seção explica a lógica de engenharia e governança adotada pelo SETISD para conectar as necessidades de negócio da ponta à construção do software.

### A Linha do Tempo: A Separação entre "Fase de Negócio" e "Fase de Engenharia"

Em qualquer projeto de software hospitalar existem dois mundos que precisam se comunicar com perfeição:
1. **O Mundo do Negócio (Chefias, Áreas Solicitantes, Governança, Direção):** Não devem ser expostos a termos técnicos de TI (bancos de dados, endpoints, JSON, status HTTP, docker, etc.). Eles precisam discutir *processos, dores reais, prazos, responsabilidades e regras*.
2. **O Mundo da Engenharia (Desenvolvedores e Testes):** Precisam de tabelas relacionais, tipos de dados estritos, rotas de API seguras e casos de uso testáveis.

Este documento (`00-validacao-negocio.md`) funciona como a **Ponte Oficial** entre esses dois mundos:

```text
               ┌────────────────────────────────────────────────────────┐
               │         00-VALIDAÇÃO E FLUXO DE NEGÓCIO (ESTE ARQUIVO)  │
FASE 1         │   Linguagem humana, fluxos e regras reais de negócio.  │
(Negócio)      │   Validado e assinado pelas Chefias e Direção do HC.   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                 ┌─────────────────────────┴─────────────────────────┐
                 ▼ (Uma vez aprovado, a TI desdobra tecnicamente)     ▼
               ┌────────────────────────────────────────────────────────┐
FASE 2         │            ARTEFATOS DE ESPECIFICAÇÃO TÉCNICA           │
(Engenharia)   │   01-visao.md  →  02-requisitos.md  →  03-casos-uso.md │
               │   04-modelo-dados.md  →  05-interfaces  →  SPEC.md     │
               └────────────────────────────────────────────────────────┘
```

---

### Como cada seção deste documento alimenta a documentação técnica:

| Seção deste Documento de Negócio | O que ela entrega para a documentação técnica? | Arquivo de Destino |
| :--- | :--- | :--- |
| **Seção 2 (O Problema que Queremos Resolver)** | Define a motivação institucional, os riscos do modelo atual e a justificativa do projeto. | [01-visao.md](01-visao.md) *(Problema e Oportunidade)* |
| **Seção 3 (Como o Processo Funciona Hoje)** | Serve de base para mapear os processos manuais que serão substituídos e os dados legados. | [01-visao.md](01-visao.md) *(Problema e Oportunidade)* |
| **Seção 4 (O Que a Nova Solução Deve Entregar)** | Define o escopo do produto e os ganhos práticos que orientam a entrega de valor. | [01-visao.md](01-visao.md) *(Escopo do Produto)* |
| **Seção 5 (Como Será o Trabalho no Novo Sistema)** | Detalha as etapas práticas do usuário na tela, que viram os fluxos e cenários de uso do sistema. | [02-requisitos.md](02-requisitos.md) e [03-casos-uso.md](03-casos-uso.md) *(Casos de Uso e Fluxos)* |
| **Seção 6 (Quem Participa do Processo)** | Define os perfis de acesso, permissões de cada papel e o modelo de autorização local. | [02-requisitos.md](02-requisitos.md) e [03-casos-uso.md](03-casos-uso.md) *(Atores e RBAC)* |
| **Seção 7 (Regras de Negócio Inegociáveis)** | As 7 regras são convertidas diretamente em requisitos funcionais estritos e validações de backend. | [02-requisitos.md](02-requisitos.md) *(Requisitos Funcionais - RFs)* |
| **Seção 8 (Painel de Gestão e Indicadores)** | Dá origem às consultas analíticas de acompanhamento, relatórios e telas gerenciais, e fornece os indicadores das metas de negócio. | [01-visao.md](01-visao.md) *(Metas e Objetivos de Negócio)* e [05-interfaces.md](05-interfaces.md) *(Protótipos e Dashboards)* |
| **Seção 9 (Matriz de Pontos de Decisão)** | Orienta os parâmetros de configuração e regras que alimentam as tarefas de implementação. | [SPEC.md](SPEC.md) *(Definições e Tarefas)* |

---

### A Regra de Ouro do Processo no SETISD:

1. **Início do Projeto (Fase de Negócio):** O profissional de TI preenche este documento junto com os responsáveis pela área de negócio em reuniões de alinhamento, validando o problema real, os fluxos práticos e as decisões pendentes.
2. **Desenvolvimento (Fase de Engenharia):** Com este documento aprovado pelas partes envolvidas, a equipe de desenvolvimento tem total clareza técnica para elaborar os artefatos de `01` a `06` e programar a solução com segurança e sem retrabalho.

**Resultado:** O cliente hospitalar participa ativamente sem ser sobrecarregado com termos técnicos, e a equipe de TI constrói exatamente o que o hospital precisa.
