# 07 — Glossário

## 1. Termos do setor (Anatomia Patológica)

### Unidades, pessoas e perfis
- **UACAP:** Unidade de Análises Clínicas e Anatomia Patológica. A Chefia do UACAP é exercida pelo Técnico Administrativo.
- **UAP:** Unidade de Anatomia Patológica; é quem recebe o exame (aparece no cabeçalho da Ficha de Trabalho).
- **Recepção:** perfil que abre o caso a partir do AGHU, recebe e confere a amostra, imprime a etiqueta e arquiva as fichas.
- **Laboratório / Técnicos:** perfil que registra macroscopia, Congelação, processamento técnico, pedidos adicionais, IHQ e envios externos; arquiva peças, blocos e lâminas.
- **Residentes:** médicos residentes que fazem a análise na Microscopia e preenchem o pré-laudo.
- **Validação / Preceptoria:** médicos patologistas que revisam o pré-laudo, validam o diagnóstico, lançam o laudo e pedem processamentos adicionais.
- **Técnico Administrativo (Chefia do UACAP):** acompanha painéis e indicadores, responde pelas decisões de negócio e gerencia os usuários e perfis do SAP.
- **Regulação do hospital:** área que cadastra no AGHU os pacientes de exames externos, com dados enviados pela Anatomia Patológica.
- **Bloco Cirúrgico:** solicita exames no AGHU, envia peças e líquidos ao setor e recebe a resposta da Congelação.

### Exames
- **HP — Histopatológico:** exame de peças e fragmentos de tecido; fluxo completo (Recepção → Macroscopia → Processamento Técnico → Microscopia → Arquivo).
- **CO — Congelação:** exame transoperatório de ciclo reduzido, com resposta rápida ao Bloco Cirúrgico. Sempre é seguido de um HP, que chega como outra solicitação.
- **IHQ — Imunohistoquímico:** exame complementar pedido pelo patologista no AGHU; não gera laudo próprio, ajuda a fechar o diagnóstico do caso original. Pode ser feito em hospital conveniado.
- **Citopatológico:** divide-se em Citologia Geral e Cérvico-vaginal.
- **CG — Citologia Geral:** citologia de líquidos e punções; pode gerar cell-block.
- **CCV — Cérvico-vaginal:** citologia do colo uterino.
- **Exame externo:** exame que chega ao HC já em alguma etapa feita fora; o SAP permite indicar a etapa inicial e marcar as etapas já realizadas.
- **Revisão da peça:** encaminhamento da Microscopia de volta à Macroscopia para nova análise da peça (só no HP).

### Registro e identificação
- **Solicitação:** pedido de exame registrado no AGHU, com número próprio. **Cada solicitação gera um caso no SAP.**
- **Número da solicitação / código do exame:** número da solicitação no AGHU (coluna "AGHU" da planilha interna). Com o prontuário, é a forma usual de localizar um caso.
- **Caso:** acompanhamento de uma solicitação no SAP, do recebimento ao arquivo, com todas as amostras, materiais derivados e movimentações.
- **Amostra:** material enviado ao setor e vinculado à solicitação no AGHU (uma solicitação pode ter várias amostras).
- **Identificador interno:** número do caso no setor, no formato `SIGLA-NNNN/AA` (ex.: `HP-0001/26`). Sigla do exame (HP, CO, IHQ, CG, CCV), número de quatro dígitos contado separadamente para cada sigla e reiniciado a cada ano, e os dois últimos dígitos do ano. Vai na etiqueta de cada peça.
- **Prontuário:** número do paciente no hospital (no AGHU e na Ficha de Trabalho como "Prnt."; na planilha interna, coluna "REGISTRO").
- **Ficha de Trabalho:** folha impressa do AGHU com dados do paciente e da solicitação; continua existindo a pedido do setor.
- **Protocolo físico:** comprovante assinado de recebimento da amostra; continua existindo a pedido do setor.
- **Etiqueta:** identificação impressa com o identificador interno, colada em cada peça.
- **Inconformidade / Rejeição:** divergência, falta de informação ou condicionamento inadequado da amostra; registrada com motivo, situação e resolução.
- **Procedimento faturável:** procedimento do fluxo com impacto no faturamento, registrado de forma estruturada.

### Etapas e materiais
- **Recepção / Triagem:** primeira etapa: conferir a amostra, registrar o recebimento e imprimir a etiqueta. (Nome da etapa; não confundir com o perfil Residentes.)
- **Fase pré-analítica:** etapas anteriores à análise microscópica (recepção, macroscopia e processamento técnico).
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
- **Pré-laudo:** rascunho do diagnóstico preenchido pelos Residentes e enviado à Preceptoria.
- **Laudo:** diagnóstico final validado pela Preceptoria e lançado no AGHU.
- **Painel / ampliação de IHQ:** conjunto de marcadores de IHQ pedido para fechar o diagnóstico.
- **Rede externa terceirizada / hospital conveniado:** destino de material enviado para processamento fora do HC (ex.: IHQ), com registro de envio e retorno.
- **Arquivo:** última etapa; caso concluído e material arquivado.
- **Encaminhamento / retorno:** movimentação do caso para outra etapa fora da ordem normal, com motivo obrigatório, sem reiniciar o processo.
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
