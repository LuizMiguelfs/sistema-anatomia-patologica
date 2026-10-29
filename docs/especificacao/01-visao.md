# Documento de Visão

## 1. Problema e Oportunidade
* **O Problema:**
  Preenchimento massivo de informações de entrada manual, feitas em planilhas, com alta probabilidade de erros. Ademais, há dificuldade de acesso e descentralização das informações encontradas no AGHU.
* **Impacto:**
  * Sobrecarga de trabalho;
  * Visibilidade precária dos dados;
  * Risco de erro no preenchimento dos dados;
  * Risco institucional e legal.
* **Solução Proposta:**
  **A Proposta de Valor:** *Centralizar o acompanhamento das solicitações e amostras em um único ambiente digital integrado ao AGHU Slave, reaproveitando automaticamente os dados já disponíveis no AGHU e permitindo o registro estruturado das informações específicas do fluxo da Anatomia Patológica. A solução deve possibilitar acompanhar cada caso ao longo das diferentes etapas do processo, desde a recepção da amostra até o processamento, análise, liberação do laudo e arquivamento, reduzindo a dependência de planilhas paralelas e consultas manuais em diferentes telas, considerando os diferentes caminhos que podem ser tomados a depender do exame.*

## 2. Partes Interessadas (Stakeholders)
* Recepção
* Laboratório/Técnicos
* Residentes
* Validação/Preceptoria
* Técnico Administrativo (Chefia do UACAP)
* Regulação do hospital (cadastro no AGHU dos pacientes de exames externos)
* Bloco Cirúrgico (solicita exames e recebe a resposta da Congelação)

## 3. Escopo do Produto
- Cobertura dos cinco tipos de exame do setor: Histopatológico (HP), Congelação (CO), Imunohistoquímico (IHQ), Citologia Geral (CG) e Cérvico-vaginal (CCV), cada um com seu caminho no fluxo. Quais entram na primeira versão depende do ponto de decisão 1 do `00-validacao-negocio.md`.
- Visualização centralizada das informações essenciais da solicitação e da amostra, evitando a necessidade de navegar por diferentes telas do AGHU para localizar dados.
- Preenchimento automático dos dados já disponíveis no AGHU Slave, reduzindo redigitação e possíveis inconsistências.
- Registro estruturado das informações produzidas dentro do SAP e que não estão contempladas adequadamente no AGHU.
- Rastreabilidade do caso ao longo das etapas do fluxo, permitindo identificar em que estágio se encontram amostras, blocos, lâminas e demais materiais relacionados.
- Redução da dependência de controles manuais e planilhas paralelas.
- Padronização dos registros de processamento, como macroscopia, blocos, cassetes, cortes, colorações, IHQ, revisões e demais procedimentos.
- Registro do laudo macroscópico, emitido ao final da macroscopia e independente do laudo final.
- Flexibilidade para exames externos: indicar a etapa inicial após o recebimento e marcar as etapas já realizadas fora do HC.
- Identificação e sinalização de pendências, inconformidades ou informações ausentes durante o processo.
- Histórico das movimentações e alterações realizadas em cada caso, com registro de etapa, responsável e data.
- Maior facilidade para localizar casos pendentes, atrasados ou que necessitam de processamento complementar.
- Apoio ao acompanhamento de materiais enviados para processamento externo, como casos de IHQ realizados em hospital conveniado.
- Consolidação de informações que possam apoiar o faturamento e reduzir o risco de procedimentos realizados não serem devidamente registrados.
- Disponibilização de informações gerenciais sobre volume de casos, etapas do fluxo, pendências, rejeições e tempos de processamento.

## 4. Metas e Objetivos de Negócio

Os **objetivos** descrevem o que o SAP precisa alcançar para o setor; as **metas** dizem como saberemos que foi alcançado. Os indicadores são os mesmos KPIs do painel de gestão definido no documento `00-validacao-negocio.md` (seção 8). Onde ainda não existe medição atual do setor, a meta numérica será definida com a Chefia do UACAP depois de medida a linha de base nas primeiras semanas de uso.

As regras que o sistema deve obedecer para atingir esses objetivos (antigas RN-01 a RN-14, agora consolidadas em 7 regras) estão na seção 7 do `00-validacao-negocio.md`.

| # | Objetivo de negócio | Indicador | Meta |
| :-: | :--- | :--- | :--- |
| **OBJ-01** | Eliminar a redigitação e a dependência de planilhas paralelas | % dos dados de paciente e solicitação preenchidos automaticamente a partir do AGHU; nº de planilhas de controle ainda em uso | 100% dos dados disponíveis no AGHU preenchidos automaticamente; planilhas dos tipos de exame do escopo substituídas pelo SAP |
| **OBJ-02** | Reduzir erros de transposição de dados | Erro de transposição (divergência entre o dado de origem e o dado registrado) | Redução em relação à linha de base; percentual a definir com a Chefia do UACAP |
| **OBJ-03** | Saber, a qualquer momento, onde está cada amostra, bloco e lâmina | % de amostras, blocos e lâminas com etapa atual consultável no sistema | 100% do material dos exames do escopo rastreável até o caso de origem |
| **OBJ-04** | Reduzir o tempo até o laudo e os atrasos | Turnaround time; taxa de cumprimento de prazos | Prazos de referência por tipo de exame definidos (ponto 2 da matriz de decisões); meta de redução a definir após a linha de base |
| **OBJ-05** | Dar visibilidade a pendências e inconformidades | Mapa de pendências e atrasos; monitoramento de inconsistências | 100% das inconformidades registradas com motivo e resolução; painel de pendências atualizado em tempo real |
| **OBJ-06** | Garantir histórico completo e auditoria do que foi feito | % de ações relevantes com autor, data/hora e valor anterior preservado | 100% das ações relevantes auditáveis |
| **OBJ-07** | Evitar perda de faturamento por falta de registro | % de procedimentos faturáveis registrados de forma estruturada | 100% dos procedimentos definidos como faturáveis (ponto 8 da matriz de decisões) registrados no sistema |
