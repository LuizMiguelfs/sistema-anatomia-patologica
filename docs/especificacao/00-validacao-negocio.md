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
  *O setor não tem um lugar onde saber em que etapa está cada solicitação de exame. O AGHU registra a chegada da solicitação e a liberação do laudo, mas não acompanha o que acontece dentro da Anatomia Patológica: macroscopia, processamento, microscopia, revisões, IHQ e envios externos. Para cobrir esse vazio, as equipes redigitam os dados do AGHU em planilhas do Teams (uma aba por tipo de exame) e anotam à mão cada etapa seguinte. Com aproximadamente 1.000 solicitações por mês e várias pessoas anotando em momentos diferentes, algumas informações às vezes deixam de ser registradas ou se perdem, e nada avisa quando isso acontece. Por isso, o setor nem sempre consegue responder com segurança "onde está este material?", "quem fez esta etapa?" ou "quanto tempo este laudo levou?".*

* **As dores, uma a uma:**

| # | Dor | O que acontece no dia a dia |
| :-: | :--- | :--- |
| **D1** | **Redigitação do que o AGHU já tem** | A recepção copia do AGHU para a planilha, solicitação por solicitação, nome, prontuário, idade, clínica, material e número da solicitação. |
| **D2** | **O AGHU não mostra a etapa interna** | O status do AGHU é genérico ("Executando", "Área executora", "Liberado"). Para saber se uma solicitação de exame está na macroscopia ou aguardando lâmina, é preciso procurar na planilha ou perguntar pelo WhatsApp. |
| **D3** | **Informações que às vezes não são registradas ou se perdem** | Cada etapa depende de alguém lembrar de anotar na planilha, no meio da rotina. Quando um dado não é anotado ou é apagado por engano, não há aviso nem histórico para recuperá-lo, e a lacuna só aparece quando alguém precisa da informação. |
| **D4** | **Registros sem padrão** | Cada pessoa escreve do seu jeito; não há listas fechadas nem conferência. O que está escrito não pode ser somado nem comparado. |
| **D5** | **Desvios do fluxo controlados à parte** | Revisão da peça, recorte, coloração especial, IHQ e envio externo ficam em abas separadas, ligadas à solicitação de origem apenas por um número digitado. |
| **D6** | **Pacientes externos chegam incompletos** | O exame externo precisa ser cadastrado pela Regulação antes de seguir, e o setor acompanha esse retorno por fora. |
| **D7** | **Dados sensíveis espalhados** | Nome, prontuário e, em algumas abas, o próprio texto do laudo ficam em planilha compartilhada no Teams; combinações sobre as solicitações correm pelo WhatsApp. |

* **Por que isso não pode continuar (Impactos Reais):**
  - **Sobrecarga de trabalho:** horas gastas digitando dados que já existem no AGHU, conferindo planilhas e perguntando pelo WhatsApp onde está cada solicitação de exame.
  - **Gestão às cegas:** como a data de liberação não fica junto com as demais etapas da solicitação, o setor não consegue medir o tempo até o laudo, nem por tipo de exame nem por etapa, sem cruzar informações à mão. Os indicadores da seção 8 hoje não têm linha de base, e a Chefia não tem como apontar onde está o gargalo.
  - **Risco ao paciente:** um material parado em uma etapa só é percebido quando alguém cobra. Nenhum alerta mostra solicitação atrasada, e exames urgentes dependem da memória da equipe.
  - **Risco institucional e legal:** a planilha compartilhada não controla quem vê nem guarda histórico de alterações, e expõe dados sensíveis (LGPD). Quando o responsável por uma etapa não é anotado, não há como comprovar depois quem a executou.
  - **Perda de faturamento:** blocos, lâminas, colorações especiais e IHQ realizados nem sempre ficam registrados na planilha, o que abre espaço para procedimentos feitos e não cobrados.

* **Quem sente a dor:**

| Quem | Como a dor aparece |
| :--- | :--- |
| **Recepção** | Redigita dados do AGHU, confere material contra a solicitação sem apoio do sistema e controla à parte os externos que aguardam a Regulação. |
| **Laboratório / Técnicos** | Anotam blocos, lâminas e saídas em planilha e papel, no meio da rotina; o que fica sem anotar não aparece para quem vem depois. |
| **Residentes** | Montam o pré-laudo consultando AGHU, planilha e lâminas em lugares diferentes. |
| **Validação / Preceptoria** | Sabem quais solicitações e pedidos (recortes, colorações, IHQ) aguardam por eles, mas essa informação está espalhada entre AGHU, planilha e conversas. Falta uma visão centralizada e com números: quantas solicitações faltam, há quanto tempo estão esperando e quais são urgentes. |
| **Chefia do UACAP** | Não tem números de volume por etapa, atraso ou tempo até o laudo; depende do que as equipes relatam. |
| **Clínicas solicitantes e pacientes** | Recebem resposta vaga sobre "quando sai o laudo", porque o próprio setor não sabe com facilidade em que etapa a solicitação está. |

---

## 3. Como o Processo Funciona Hoje (A Rotina Atual)

> **Objetivo:** Mapear a realidade crua de como as equipes se viram no dia a dia para realizar essa tarefa hoje.

* **Meios Utilizados Hoje:**
  - **AGHU:** aceite da solicitação, devolução de solicitações com inconformidade, impressão da Ficha de Trabalho e lançamento do laudo final. Não registra as etapas internas do setor.
  - **Planilha no Teams:** uma aba por tipo de controle (HP, HP Dermatologia, Congelação, IHQ, Citologia Geral, Cérvico-vaginal, Revisão interna, Casos em revisão e Rejeição de amostras), preenchida à mão a cada etapa.
  - **Papel:** protocolo de recebimento assinado (data e nome de quem recebeu) e Ficha de Trabalho impressa que acompanha o material.
  - **WhatsApp:** comunicação rápida entre as equipes, inclusive para localizar solicitações.
  - **Sistemas externos:** SISCAN (cadastro dos exames que o exigem, na etapa de arquivo) e CMCE da SES-PE (agendamento de parte dos exames externos, conferido na recepção).

* **Volume e perfil da demanda** (valores aproximados, de um recorte de período recente): cerca de **1.000 solicitações e 1.500 itens de exame por mês**; aproximadamente 1 em cada 4 solicitações traz mais de uma amostra.

| Tipo de exame | Participação aproximada |
| :--- | ---: |
| Histopatológico (peça cirúrgica, biópsia, mama, colo uterino) | ~74% |
| Cérvico-vaginal (CCV) | ~8% |
| Histopatológico de Dermatologia | ~7% |
| Imunohistoquímico (IHQ) | ~6% |
| Citopatológico / Citologia Geral (inclui mama e oncótica) | ~4% |
| Congelação (CO) | ~1,5% |

  Por origem, também de forma aproximada: ambulatório ~44%, internação ~31%, paciente externo ~13% e cirurgia ~11%.

* **Tipos de Exame do Setor:**  
  Histopatológico (HP), Congelação (CO), Imunohistoquímico (IHQ), Citologia Geral (CG) e Cérvico-vaginal (CCV). O Imunohistoquímico complementa um exame em curso e pode participar do fechamento do diagnóstico: ele gera um laudo próprio, que é anexado ao laudo principal do exame que complementa. Na prática, o setor também controla em separado o **Histopatológico de Dermatologia** (aba própria) e as **Revisões de lâmina** (solicitações de revisão que entram direto na Microscopia, conforme o esquema do fluxo).

* **A Rotina Prática de Trabalho:**
  1. **Início:** No AGHU, é aceita a solicitação do exame. O material chega das unidades assistenciais, do Bloco Cirúrgico ou de fora do hospital (a fresco, em fixador, ou já em blocos e lâminas). A recepção confere o material contra a solicitação (no AGHU, para internos; documentação e requisição, para externos). Se houver inconformidade, a solicitação é devolvida no AGHU, o material volta ao setor de origem e a ocorrência é anotada na aba de Rejeição, que já usa uma lista de 14 motivos padronizados. Estando correta, a solicitação é cadastrada na aba da planilha do seu tipo de exame; se for exame externo, os dados são enviados à Regulação para cadastro no AGHU.
  2. **Fase Pré-Analítica:** Para sair da recepção, é assinado o protocolo físico, com data e nome do profissional que recebeu as amostras, e a Ficha de Trabalho impressa do AGHU acompanha o material. Cada informação seguinte (macroscopia, fragmentos, blocos, lâminas, técnico, datas de saída) deveria ser anotada nos campos da planilha. A macroscopia gera um laudo próprio ao seu final, além do laudo final emitido após a microscopia. A Congelação segue um ciclo reduzido com equipe de plantão e, depois, o material volta à recepção para o fluxo do Histopatológico.
  3. **Fase Analítica:** Residentes e Preceptoria analisam as lâminas e tentam fechar o diagnóstico. Se não fecha, a solicitação volta à fase pré-analítica (revisão da peça, recorte ou coloração especial, painel ou ampliação de IHQ) ou é enviada para a rede externa terceirizada. Esses retornos são controlados em abas separadas (IHQ, Casos em revisão), ligadas à solicitação de origem apenas pelo número digitado.
  4. **Fase Pós-Analítica:** O laudo é lançado no AGHU e gerado em PDF; quando houver IHQ, o laudo da IHQ é anexado ao laudo principal. Quando necessário, o exame é cadastrado no SISCAN; a ficha é arquivada.

* **O que já funciona e deve ser preservado:** o protocolo físico e a Ficha de Trabalho impressa (mantidos a pedido do setor), a lista de 14 motivos de rejeição já padronizada na planilha e a numeração interna `SIGLA-NNNN/AA`, que o setor já usa.

---

## 4. O Que a Nova Solução Deve Entregar (Resultado Esperado)

> **Objetivo:** Definir com clareza o que a solução digital deve trazer para eliminar a dor do processo atual.

* **A Proposta de Valor:** *Centralizar o acompanhamento das solicitações de exame e amostras em um único ambiente digital integrado ao AGHU Slave, reaproveitando automaticamente os dados já disponíveis no AGHU e permitindo o registro estruturado das informações específicas do fluxo da Anatomia Patológica. A solução deve possibilitar acompanhar cada solicitação de exame ao longo das diferentes etapas do processo, desde a recepção da amostra até o processamento, análise, liberação do laudo e arquivamento, reduzindo a dependência de planilhas paralelas e consultas manuais em diferentes telas, considerando os diferentes caminhos que podem ser tomados a depender do exame.*

* **Ganhos Práticos Imediatos:**
  - Visualização centralizada das informações essenciais da solicitação e da amostra, evitando a necessidade de navegar por diferentes telas do AGHU para localizar dados.
  - Preenchimento automático dos dados já disponíveis no AGHU Slave, reduzindo redigitação e possíveis inconsistências.
  - Registro estruturado das informações produzidas dentro do SAP e que não estão contempladas adequadamente no AGHU.
  - Rastreabilidade da solicitação de exame ao longo das etapas do fluxo, permitindo identificar em que estágio se encontram amostras, blocos, lâminas e demais materiais relacionados.
  - Redução da dependência de controles manuais e planilhas paralelas.
  - Padronização dos registros de processamento, como macroscopia, blocos, cassetes, cortes, colorações, IHQ, revisões e demais procedimentos.
  - Identificação e sinalização de pendências, inconformidades ou informações ausentes durante o processo.
  - Histórico das movimentações e alterações realizadas em cada solicitação de exame, com registro de etapa, responsável e data.
  - Maior facilidade para localizar solicitações pendentes, atrasadas ou que necessitam de processamento complementar.
  - Apoio ao acompanhamento de materiais enviados para processamento externo, como IHQ realizada em hospital conveniado.
  - Consolidação de informações que possam apoiar o faturamento e reduzir o risco de procedimentos realizados não serem devidamente registrados.
  - Disponibilização de informações gerenciais sobre volume de solicitações, etapas do fluxo, pendências, rejeições e tempos de processamento.

---

## 5. Como Será o Trabalho no Novo Sistema (O Novo Fluxo)

> **Objetivo:** Explicar em linguagem direta como o usuário vai interagir com o sistema, resolvendo a dor do processo manual de ponta a ponta.

* **1. Os dados já vêm prontos:** O usuário não precisa mais digitar dados do paciente ou da solicitação do zero, nem pular de tela em tela no AGHU para juntar informações. Ao abrir o sistema, os dados essenciais da amostra e da solicitação já vêm preenchidos automaticamente do AGHU Slave, sem possibilidade de edição (RN-01). Isso elimina a redigitação, evita inconsistências e centraliza tudo em uma única visualização.
* **2. Devolução da solicitação com justificativa:** Na recepção, se o material ou a solicitação apresentar alguma inconformidade, será possível devolver a solicitação de exame e a coleta ao setor de origem pelo próprio sistema. A devolução contará com uma caixa de texto, de preenchimento opcional, para explicar por que a solicitação está sendo devolvida. A solicitação devolvida não é excluída: ela é encerrada como se já tivesse um resultado, mas com o status "Devolvida" ou "Cancelada" (nome a definir) no lugar de "Concluída", e todo o seu histórico continua disponível (detalhamento na RN-06). Como o AGHU também tem a opção de devolver a solicitação, a recepção precisaria registrar a devolução nos dois lugares; a forma de evitar esse retrabalho ainda será definida (ponto de decisão 10).
* **3. Preenchimento rápido com travas contra erros:** O registro das etapas que não existem no AGHU (como macroscopia, blocos, cassetes, cortes, colorações, IHQ e revisões) é feito direto em formulários padronizados no novo ambiente. O sistema identifica e sinaliza ativamente qualquer pendência, inconformidade ou informação ausente, reduzindo a dependência de controles em papel e de planilhas paralelas.
* **4. Cada movimentação fica registrada:** A cada avanço do material, da recepção ao arquivamento, o sistema registra automaticamente a etapa, a data, a hora e o responsável pela movimentação. Com isso, saber exatamente onde está uma amostra, um bloco ou uma lâmina (inclusive materiais enviados para processamento externo, como IHQ conveniada) vira uma simples consulta na tela, amparada por um histórico de auditoria completo. A pedido do setor, a Ficha de Trabalho impressa e o protocolo físico de recebimento continuam existindo ao lado desse registro.
* **5. Informação pronta e disponível:** A equipe e a gestão visualizam em painéis atualizados o que está pendente, atrasado ou precisando de complemento. Além de facilitar a rotina de quem está na bancada, o sistema consolida o volume de solicitações, rejeições e tempos de processamento, reduzindo o risco de que algum procedimento realizado deixe de ser faturado por falta de registro.
* **6. Exames externos com ponto de partida flexível:** Quando chega um exame externo sem cadastro, a recepção registra no sistema o encaminhamento dos dados à Regulação, e o exame fica numa lista de "aguardando cadastro", sem que precise ser controlado por fora. Ele só aparece como solicitação de exame depois que a Regulação cadastra o paciente e abre a solicitação no AGHU (RN-02); nesse momento, o encaminhamento é vinculado à solicitação. Exames externos podem chegar ao HC em diferentes níveis de evolução: a partir daí, o sistema permite indicar por qual etapa o exame começa e marcar as etapas que já foram realizadas fora do HC.

---

## 6. Quem Participa do Processo (Atores: Como Faz Hoje vs. Como Fará no Sistema)

| Ator / Perfil no Hospital   | O que faz HOJE (Rotina Manual)                                                                                                                | O que passará a fazer no NOVO SISTEMA                                                                                                     | O que NÃO poderá fazer                                                    |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------ |
| **Recepção**                | Cadastrar manualmente as amostras recebidas na planilha e anexar o identificador interno em cada peça.                                        | Revisão de cadastramento das amostras, registro do encaminhamento de exames externos à Regulação, devolução de solicitações com inconformidade e anexo da etiqueta com identificador interno impresso em cada peça. | Alterar dados vindos do AGHU (RN-01).                        |
| **Laboratório / Técnicos**  | Criam relatório impresso e planilha do Teams, correndo risco de esquecer dados ou duplicar lançamentos. Realizam fase pré-analítica.          | Lançam os dados direto no sistema com validações em tempo real e encaminham relatórios pré-processados para conferência da chefia.        | Alterar dados de setores que não sejam de sua alçada.                     |
| **Residentes**              | Preenchimento de pré-laudo após análise da peça no AGHU e Teams.                                                                              | Preenchem em uma tela única o pré-laudo após análise, pronto para ser enviado ao preceptor.                                               | Alterar dados de setores que não sejam de sua alçada.                     |
| **Validação / Preceptoria** | Revisar o pré-laudo e escrever o diagnóstico, enviando os resultados pelo AGHU. Pode solicitar processamentos adicionais ao laboratório.      | Revisar o pré-laudo e escrever o diagnóstico, enviando os resultados pelo AGHU. Pode solicitar processamentos adicionais direto do sistema, que ficam vinculados à solicitação de exame. | Alterar dados de setores que não sejam de sua alçada.                     |
| **Técnico Administrativo (Chefia do UACAP)** | Acompanhar o andamento do setor sem uma visão consolidada, dependendo de planilhas e de informações repassadas pelas equipes.                 | Acompanhar painéis de pendências, atrasos, rejeições, volume de solicitações e tempos de processamento, responder pelas decisões da seção 9 e gerenciar quem acessa o SAP e com qual perfil (incluir usuário, alterar perfil, inativar ou reativar acesso).   | Apagar ou sobrescrever o histórico de registros feitos pelas equipes; alterar o próprio perfil ou inativar o próprio acesso.     |

> **Nota sobre nomes:** "Recepção / Triagem" é o nome da primeira **etapa** do fluxo. O perfil de quem faz o pré-laudo chama-se apenas **Residentes**, para não confundir os dois. **Preceptor e patologista são a mesma pessoa:** o perfil **Validação / Preceptoria** é o dos patologistas do setor. **UACAP** é a Unidade de Análises Clínicas e Anatomia Patológica.

**Definições confirmadas com o setor:**
- **Congelação e Histopatológico são duas solicitações de exame.** Quando há Congelação, o material chega com duas solicitações diferentes no AGHU (CO e HP), e cada uma é acompanhada separadamente no SAP. Sempre que há Congelação, há um Histopatológico depois.
- **Identificador interno:** `SIGLA-NNNN/AA`, por exemplo `HP-0001/26`. A sigla é a do tipo de exame (HP, CO, IHQ, CG ou CCV); o número tem quatro dígitos, é contado separadamente para cada sigla e recomeça em 0001 a cada ano; `AA` são os dois últimos dígitos do ano.

**Outros participantes do processo:**
- **Regulação do hospital:** cadastra no AGHU os pacientes de exames externos, a partir dos dados enviados pela Anatomia Patológica.
- **Bloco Cirúrgico:** solicita exames no AGHU, envia peças e líquidos ao setor e recebe da equipe a resposta da Congelação.

A forma como esses dois participantes vão interagir com o SAP ainda não foi definida.

---

## 7. Regras de Negócio Inegociáveis (RNs)

> Sete regras que o sistema deve cumprir sempre. Elas reúnem, sem perder conteúdo, as 14 regras da versão anterior.

- **RN-01 (Fonte Oficial do AGHU, Dados Imutáveis e Separação dos Dados):** as informações já disponíveis no AGHU devem ser obtidas automaticamente por meio da base institucional disponibilizada pelo HC-UFPE, evitando a redigitação desnecessária de dados clínicos e administrativos. **Os dados trazidos do AGHU são imutáveis no SAP: não é permitida a edição de nenhum deles, por nenhum perfil.** Se um dado do AGHU estiver errado, a correção deve ser feita no próprio AGHU, e o SAP passa a exibir o valor corrigido. O sistema não deve manter cópias manuais divergentes dessas informações. Os dados originados no AGHU são tratados como dados da fonte institucional; os dados gerados durante o processamento da Anatomia Patológica são armazenados e mantidos pelo SAP. O sistema deve deixar clara essa distinção e manter a vinculação entre ambos.
- **RN-02 (Origem Exclusiva no AGHU, Vínculo e Rastreabilidade):** **o SAP não abre nenhuma solicitação de exame que não exista antes no AGHU.** A solicitação de exame e os seus dados primários (os que antecedem os dados criados durante a execução do exame) vêm exclusivamente do AGHU; não é possível criar uma solicitação de exame diretamente no SAP. Exames externos também seguem essa regra: só passam a existir como solicitação de exame no SAP depois que a Regulação cadastra o paciente e abre a solicitação no AGHU. Antes disso, o SAP registra apenas o **encaminhamento à Regulação** (dados enviados, data e responsável), que não é uma solicitação de exame, não recebe identificador interno nem pode ser processado; quando a solicitação aparece no AGHU, o encaminhamento é vinculado a ela. Fora esse encaminhamento, toda amostra processada deve estar obrigatoriamente vinculada à solicitação e aos identificadores correspondentes no AGHU; o sistema não deve permitir a criação ou o processamento de registros sem que seja possível determinar, sem possibilidade de erro, a qual solicitação e amostra eles pertencem. Os materiais derivados (peças, cassetes, blocos, lâminas e outros) devem permanecer rastreáveis até a solicitação de exame de origem durante todo o processo. Procedimentos complementares (recortes, novas colorações, IHQ, revisão) e encaminhamentos externos devem permanecer associados à solicitação original e não podem gerar registros isolados. Nos encaminhamentos externos, devem constar envio, finalidade, situação e retorno do material ou resultado.
- **RN-03 (Progressão Controlada do Fluxo e Status Confiável):** uma etapa só pode ser registrada como concluída quando as informações obrigatórias tiverem sido preenchidas; pendências, inconformidades ou ausência de dados essenciais devem impedir ou sinalizar o avanço indevido da solicitação de exame, evitando retrabalho. O status exibido deve ser derivado ou validado a partir das etapas efetivamente registradas: uma solicitação não pode aparecer como concluída, liberada ou arquivada enquanto existirem etapas obrigatórias ou pendências incompatíveis com esse estado (por exemplo: informação crítica não preenchida, etapa ignorada ou alteração pendente).
- **RN-04 (Histórico, Autoria e Auditoria):** registros anteriores não devem ser apagados nem sobrescritos de forma a eliminar o histórico da solicitação de exame; toda alteração relevante preserva a informação anterior e a nova, permitindo reconstruir a trajetória do material e das decisões. Toda ação relevante deve estar associada ao usuário autenticado, com data/hora, ação executada e recurso afetado, e a etapa executada ou concluída deve identificar o profissional responsável. As alterações de dados clínicos ou operacionais devem ter trilha de auditoria conforme o padrão institucional do HC-UFPE, informado pelo líder técnico do SETISD (Daniel Turmina).
- **RN-05 (Autenticação Institucional e Controle de Acesso):** o acesso ao sistema deve ocorrer por autenticação institucional, utilizando os mecanismos previstos pelo framework do HC-UFPE disponível no repositório. As funcionalidades de cada usuário devem respeitar os perfis e permissões definidos pelo controle de acesso institucional.
- **RN-06 (Registro de Inconformidades, Rejeições e Devoluções):** amostras com divergências, ausência de informações, condicionamento inadequado ou outras inconformidades não podem seguir o fluxo normal sem que a ocorrência seja registrada. O sistema deve manter o motivo, a situação e a resolução da inconformidade vinculados à solicitação de exame. Quando a inconformidade levar à devolução da solicitação de exame e da coleta ao setor de origem, a devolução deve ser registrada com o motivo, data, hora e responsável (RN-04), e pode trazer uma explicação em caixa de texto (preenchimento opcional) sobre por que a solicitação está sendo devolvida. A solicitação devolvida não é excluída: é encerrada com um status final próprio ("Devolvida" ou "Cancelada", nome a definir), distinto de "Concluída".
- **RN-07 (Registro de Procedimentos Relevantes ao Faturamento):** procedimentos realizados ao longo do fluxo que tenham impacto administrativo ou de faturamento devem ser registrados de forma estruturada, evitando que sua contabilização dependa exclusivamente de anotações manuais ou controles paralelos.

---

## 8. Painel de Gestão e Indicadores Estratégicos (KPIs)

| Indicador | O que mede |
| :--- | :--- |
| **Turnaround time** | Tempo total entre a recepção da amostra e a emissão do laudo conclusivo. |
| **Erro de transposição** | Divergências entre o dado de origem e o dado registrado. |
| **Taxa de cumprimento de prazos** | Proporção de solicitações de exame concluídas dentro do prazo de referência de cada tipo de exame. |
| **Mapa de pendências e atrasos** | Solicitações pendentes, atrasadas ou aguardando processamento complementar, por etapa. |
| **Automação do preenchimento** | Proporção de dados que chegam do AGHU sem digitação manual. |
| **Rastreabilidade (status das amostras)** | Etapa atual de cada amostra, bloco e lâmina. |
| **Monitoramento de inconsistências** | Inconformidades, rejeições e devoluções registradas, com motivo e situação de resolução. |

---

## 9. Matriz de Pontos de Decisão (Chefia do UACAP / Gestão do Negócio)

> **Como ler esta matriz:** cada linha é uma pergunta que o sistema não consegue responder sozinho e que a equipe de TI não deve decidir no lugar do hospital. A coluna "Por que precisa ser decidido" explica o que muda no sistema conforme a resposta; "Opções em discussão" traz caminhos possíveis para facilitar a conversa, e não decisões já tomadas. Quando houver resposta, o status muda para 🟢 Decidido, com a data e a definição registradas na própria linha.

| # | Ponto a decidir | Por que precisa ser decidido (o que muda no sistema) | Opções em discussão | Quem deve decidir? | Status / Definição |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Tipos de exame da primeira versão:** quais tipos de exame entram na primeira entrega do sistema? | Hoje há uma planilha por tipo de exame e cada tipo começa em uma fase diferente. O sistema precisa de um fluxo para cada tipo, então quanto mais tipos na primeira versão, maior e mais demorada a entrega. | Começar por um ou dois tipos (por exemplo, histopatológico) e ampliar depois; ou entregar todos os tipos de uma vez. | Chefia do UACAP | 🟡 Em definição |
| **2** | **Prazos de referência:** qual o prazo esperado para cada tipo de exame (e, se necessário, para cada etapa)? | Define o que o sistema considera "atrasado", quando dispara alertas e como é calculada a taxa de cumprimento de prazos. Sem prazo definido, o painel não consegue apontar atrasos. | Um prazo único para todos os exames; um prazo por tipo de exame; prazos por etapa do fluxo. | Chefia do UACAP, com Preceptoria | 🟡 Em definição |
| **3** | **Retorno à fase pré-analítica:** quando o diagnóstico não fecha, quem decide que a solicitação de exame volta e o que precisa ser informado? | O sistema precisa saber se o retorno exige motivo obrigatório e quem pode pedi-lo. A solicitação volta a uma etapa anterior sem apagar o histórico do que já foi feito (RN-04). | O profissional responsável pela etapa em que a solicitação está define o encaminhamento ou retorno (é o que diz o feedback do fluxo atual; falta confirmar quem é esse responsável na Microscopia); apenas a Preceptoria pode retornar a solicitação à etapa anterior, com motivo obrigatório; ou Residentes também podem sugerir o retorno, com confirmação da Preceptoria. | Preceptoria e Chefia do UACAP | 🟡 Em definição |
| **4** | **Pedido de processamentos adicionais:** o que a Preceptoria pode pedir pelo sistema (novos cortes, colorações, IHQ, revisão), para quem o pedido vai e se precisa de aprovação? | Define o formulário de pedido, quem recebe o aviso e se o pedido entra direto na fila do laboratório. Todo pedido fica vinculado à solicitação de exame original (RN-02). | Pedido direto da Preceptoria para o Laboratório; ou pedido com aprovação prévia da Chefia. | Preceptoria e Chefia do UACAP | 🟡 Em definição |
| **5** | **Correção após laudo liberado:** qual o rito para corrigir ou reabrir um laudo ou dado já concluído? | Define se haverá reabertura formal, com justificativa gravada e laudo anterior preservado (RN-04), e quem tem permissão para fazê-la. Também precisa considerar que o laudo já foi lançado no AGHU. | Reabertura apenas pela Chefia, com justificativa obrigatória; ou pelo Preceptor responsável, com justificativa e aviso à Chefia. | Chefia do UACAP, com apoio do SETISD no que envolver o AGHU | 🟡 Em definição |
| **6** | **Substituição na ausência:** quem valida o laudo e responde pelas decisões quando o preceptor ou a chefia titular estiver de férias ou afastado? | Evita que solicitações fiquem paradas por ausência de uma única pessoa. Define quem recebe as permissões de validação temporariamente. | Lista fixa de substitutos cadastrados; ou delegação temporária registrada pela própria Chefia. | Chefia do UACAP | 🟡 Em definição |
| **7** | **IHQ em hospital conveniado:** o que deve ser registrado no envio e no retorno do material, e quem confirma o recebimento? | Define os campos do encaminhamento externo (envio, finalidade, situação e retorno, conforme RN-02), o prazo esperado de retorno e o alerta para material que não voltou. | Registro feito pelo Laboratório no envio e no retorno; ou envio pelo Laboratório e confirmação de retorno pela Preceptoria. | Chefia do UACAP e Laboratório | 🟡 Em definição |
| **8** | **Procedimentos que contam para o faturamento:** quais procedimentos realizados no fluxo têm impacto no faturamento? | O sistema só consegue registrar de forma estruturada (RN-07) o que estiver numa lista definida. Sem essa lista, o risco de procedimento não faturado continua. | Lista fornecida pela Chefia, validada com a área de faturamento do hospital. | Chefia do UACAP, com a área de faturamento do HC-UFPE | 🟡 Em definição |
| **9** | **Transição das planilhas:** por quanto tempo planilhas e sistema funcionam em paralelo, e o que acontece com o histórico das planilhas do Teams? | Define a data de início do uso oficial do SAP, se o histórico antigo será levado para o sistema ou apenas consultado nas planilhas, e quando as planilhas deixam de ser atualizadas. | Período curto de uso paralelo com data de corte; ou virada direta por tipo de exame. Histórico: migrar, ou manter planilhas apenas para consulta. | Chefia do UACAP e SETISD | 🟡 Em definição |
| **10** | **Devolução no SAP e no AGHU:** como evitar que a recepção registre a mesma devolução duas vezes? | A devolução da solicitação de exame existe no AGHU e passará a existir no SAP, com motivo e explicação opcional em texto (RN-06). Sem uma definição, a recepção registra a devolução nos dois sistemas, o que gera retrabalho e risco de os registros não baterem. | Registrar no SAP e devolver no AGHU, com o SAP indicando o passo pendente no AGHU; registrar só no AGHU e o SAP apenas exibir a devolução, se a informação puder ser lida do AGHU; ou outra forma a avaliar com o SETISD. | Chefia do UACAP e Recepção, com apoio do SETISD | 🟡 Em definição |

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
