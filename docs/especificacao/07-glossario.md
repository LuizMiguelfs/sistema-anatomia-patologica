# 07 — Glossário

## 1. Termos do setor (Anatomia Patológica)

### Unidades, pessoas e perfis
- **UACAP:** Unidade de Análises Clínicas e Anatomia Patológica. A Chefia do UACAP é exercida pelo Técnico Administrativo.
- **UAP:** Unidade de Anatomia Patológica; é quem recebe o exame (aparece no cabeçalho da Ficha de Trabalho).
- **Recepção:** perfil que acompanha as solicitações recebidas no AGHU, confere a amostra, marca no SAP quando o material é retirado da recepção e arquiva as fichas. O recebimento é registrado no AGHU (etiquetas: a confirmar com o setor).
- **Laboratório / Técnicos:** perfil que registra o Processamento Técnico e a IHQ, os pedidos adicionais e os envios externos; arquiva peças, blocos e lâminas.
- **Residentes:** médicos residentes que registram a Macroscopia e preenchem o pré-laudo da Congelação, da Microscopia e da Revisão de Lâmina.
- **Validação / Preceptoria (patologista):** médicos patologistas que revisam o pré-laudo, validam o diagnóstico, concluem a Congelação, a Microscopia e a Revisão de Lâmina, lançam o laudo e pedem processamentos adicionais. Preceptor e patologista são a mesma pessoa.
- **Técnico Administrativo (Chefia do UACAP):** acompanha painéis e indicadores, responde pelas decisões de negócio e gerencia os usuários e perfis do SAP.
- **Regulação do hospital:** área que cadastra no AGHU os pacientes de exames externos, com dados enviados pela Anatomia Patológica.
- **Bloco Cirúrgico:** solicita exames no AGHU, envia peças e líquidos ao setor e recebe a resposta da Congelação.

### Exames
- **HP — Histopatológico:** exame de peças e fragmentos de tecido; fluxo completo (Recepção → Macroscopia → Processamento Técnico → Microscopia → Arquivo).
- **CO — Congelação:** exame transoperatório de ciclo reduzido, com resposta rápida ao Bloco Cirúrgico. Sempre é seguido de um HP, que chega como outra solicitação.
- **IHQ — Imunohistoquímico:** exame complementar pedido pelo patologista, quando o diagnóstico não fecha; gera um laudo próprio, anexado ao laudo principal da solicitação original. Pode ser feito em hospital conveniado.
- **Citopatológico:** divide-se em Citologia Geral e Cérvico-vaginal.
- **CG — Citologia Geral:** citologia de líquidos e punções; pode gerar cell-block.
- **CCV — Cérvico-vaginal:** citologia do colo uterino.
- **Exame externo:** exame que chega ao HC já em alguma etapa feita fora; o SAP permite indicar a etapa inicial e marcar as etapas já realizadas.
- **RL — Revisão de Lâmina:** solicitação de revisão de lâminas, que no SAP entra direto na fila da Revisão de Lâmina.
- **Revisão da peça:** encaminhamento da Microscopia de volta à Macroscopia para nova análise da peça (só no HP).

### Registro e identificação
- **Solicitação de exame:** pedido de exame registrado no AGHU, com número próprio. É a unidade de trabalho do SAP: entra quando é recebida no AGHU e é acompanhada até o arquivo, com amostras, materiais derivados, formulários de cada fase e movimentações. O SAP não cria solicitações (RN-02).
- **Número da solicitação / código do exame (código AGHU):** número da solicitação no AGHU (coluna "AGHU" da planilha interna). Com o prontuário e o código interno, é a forma usual de localizar uma solicitação.
- **Amostra:** material enviado ao setor e vinculado à solicitação no AGHU (uma solicitação pode ter várias amostras).
- **Identificador interno (código interno):** número da solicitação no setor, no formato `SIGLA-NNNN/AA` (ex.: `HP-0001/26`). Sigla do exame (HP, CO, IHQ, CG, CCV, RL), número de quatro dígitos contado separadamente para cada sigla e reiniciado a cada ano, e os dois últimos dígitos do ano. Vai na etiqueta de cada peça.
- **Prontuário:** número do paciente no hospital (no AGHU e na Ficha de Trabalho como "Prnt."; na planilha interna, coluna "REGISTRO").
- **Ficha de Trabalho:** folha impressa do AGHU com dados do paciente e da solicitação; continua existindo a pedido do setor.
- **Protocolo físico:** comprovante assinado de recebimento da amostra; continua existindo a pedido do setor.
- **Etiqueta:** identificação impressa com o identificador interno, colada em cada peça.
- **Inconformidade / Rejeição:** divergência, falta de informação ou condicionamento inadequado da amostra; registrada com motivo, situação e resolução.
- **Procedimento faturável:** procedimento do fluxo com impacto no faturamento, registrado de forma estruturada.

### Etapas e materiais
- **Recepção / Triagem:** primeira etapa: conferir a amostra e entregar o material ao setor. No SAP, a etapa termina quando a Recepção marca a solicitação como **retirada**. (Nome da etapa; não confundir com o perfil Residentes.)
- **Não retirado / Retirado:** situação da solicitação na Recepção. Não retirada: recebida no AGHU e ainda na Recepção. Retirada: o material saiu da Recepção e a solicitação seguiu para a primeira fase do seu tipo de exame. A retirada pode ser desfeita enquanto a fase seguinte não registrou nada.
- **Fase pré-analítica:** etapas anteriores à análise microscópica. No menu do SAP: Macroscopia, Congelação, Processamento Técnico e IHQ.
- **Fase analítica:** análise das lâminas e diagnóstico. No menu do SAP: Microscopia e Revisão de Lâmina.
- **Fila da fase:** lista das solicitações que estão naquela fase agora, com as urgentes no topo e, depois, da mais antiga para a mais recente. As concluídas ficam mais 6 dias na lista para edição.
- **Urgente:** solicitação que passa à frente nas filas. Toda Congelação é urgente.
- **Salvar / Concluído:** os dois botões do formulário de cada fase. Salvar guarda um **rascunho** sem exigir os campos obrigatórios; Concluído exige os obrigatórios, pede confirmação e envia a solicitação para a próxima fase.
- **Macroscopia:** descrição a olho nu da peça e geração dos cassetes; termina com o laudo macroscópico.
- **Laudo macroscópico:** laudo emitido ao final da Macroscopia, independente do laudo final.
- **Análise macroscópica preliminar:** análise feita na Congelação (não na Macroscopia).
- **Processamento técnico:** preparo do material até a lâmina: Histotécnico ou Preparo manual, Inclusão, Corte, Coloração e Montagem.
- **Histotécnico:** processamento automatizado do tecido; alternativa ao Preparo manual.
- **Preparo manual:** processamento manual do tecido; alternativa ao Histotécnico.
- **Inclusão:** colocação do tecido em parafina, formando o bloco.
- **Corte:** fatiamento do bloco em cortes finos para as lâminas.
- **Coloração:** coloração dos cortes ou do material citológico; **coloração especial** é pedida quando o diagnóstico não fecha.
- **Montagem:** finalização da lâmina para análise.
- **Distribuição:** entrega das lâminas de citologia para a Microscopia.
- **Centrifugação:** etapa do material citológico líquido.
- **Cell-block:** bloco feito a partir de fragmento encontrado em líquido citológico; passa pela bancada do HP e volta à Coloração na Citologia.
- **Bancada:** posto de trabalho de cada processamento (bancada do HP, bancada da Citologia).
- **Peça:** material cirúrgico recebido.
- **Cassete:** recipiente com fragmentos da peça gerado na Macroscopia.
- **Bloco:** cassete com tecido incluído em parafina.
- **Lâmina:** corte ou esfregaço montado para a Microscopia.
- **Recorte:** novo corte de um bloco, pedido na Microscopia.
- **Microscopia:** análise das lâminas e preenchimento do pré-laudo.
- **Pré-laudo:** rascunho do diagnóstico preenchido pelos Residentes e enviado à Preceptoria. Salvo no formulário, a solicitação passa a aparecer no Início como **aguardando o patologista**.
- **Laudo:** diagnóstico final validado pela Preceptoria e lançado no AGHU.
- **Painel / ampliação de IHQ:** conjunto de marcadores de IHQ pedido para fechar o diagnóstico.
- **Rede externa terceirizada / hospital conveniado:** destino de material enviado para processamento fora do HC (ex.: IHQ), com registro de envio e retorno.
- **Arquivo:** última etapa; solicitação concluída e material arquivado.
- **Encaminhamento / retorno:** movimentação da solicitação para outra etapa fora da ordem normal (ex.: IHQ pedida na Microscopia), com motivo obrigatório, sem reiniciar o processo. Ao concluir a etapa para onde foi encaminhada, a solicitação volta à etapa de origem. No painel, as encaminhadas que ainda não voltaram aparecem como **aguardando complementação**.
- **Histórico da solicitação (linha do tempo):** o que foi feito com a solicitação, por quem e quando, na ordem, montado a partir da trilha de auditoria. Todos os perfis veem.
- **TAT (turnaround time):** tempo decorrido entre marcos de um exame (da recepção ao laudo).

## 2. Termos técnicos
- **AD / LDAP:** diretório e protocolo de autenticação corporativa.
- **AGHU:** Aplicativo de Gestão para Hospitais Universitários; fonte externa para consultas clínicas/administrativas. O SAP lê o **AGHU Slave** (cópia somente leitura).
- **SAP:** Serviço de Anatomia Patológica, o sistema desta especificação.
- **RBAC:** controle de acesso baseado em papéis e permissões.
- **JWT:** token de acesso assinado usado na API.
- **Refresh token:** credencial de renovação de sessão, guardada de forma controlada e transmitida via cookie HttpOnly.
- **SPA:** aplicação web de página única, neste projeto Vue 3.
- **Provider:** adaptação da camada de dados a uma fonte (CSV, PostgreSQL, SQLite).
- **DSN:** string de configuração de conexão a banco.
- **Alembic:** ferramenta de versionamento de esquemas relacionais.
- **Head:** última revisão de uma linha de migração Alembic; múltiplos heads exigem conciliação.
- **Auditoria imutável:** histórico de ações, sem atualização/exclusão do registro anterior.
- **Soft delete (exclusão lógica):** o registro não é apagado; é marcado (`deleted_at`) ou inativado.
- **AES-256:** criptografia simétrica com chave de 256 bits usada nos dados sensíveis gravados pelo SAP (modo GCM).
- **MFA:** autenticação com mais de um fator (ex.: senha + código).
- **TCLE:** Termo de Consentimento Livre e Esclarecido.
- **LGPD:** Lei Geral de Proteção de Dados Pessoais.
- **SETISD / HC-UFPE:** setor de tecnologia e Hospital das Clínicas da UFPE, conforme contexto deste projeto.
- **AGHU simulado:** provedor de desenvolvimento que lê solicitações fictícias de `data/aghu_simulado.json` no lugar do AGHU; serve só para demonstração.
- **Carga de demonstração:** `python -m scripts.seed_mvp --confirm`, que cria usuários e solicitações fictícias espalhadas pelas filas. Recusa produção e bancos que já têm solicitações.
- **CI (integração contínua):** checagem automática do GitHub Actions em cada PR: testes do backend e do frontend, build e auditor do framework.
