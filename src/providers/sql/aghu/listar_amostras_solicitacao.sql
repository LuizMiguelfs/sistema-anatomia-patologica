-- SOMENTE LEITURA (RNF005). Nomes de tabela/coluna do AGHU: VALIDAR com o DBA/SETISD.
SELECT ise.soe_seq AS solicitacao_aghu,
       ise.seqp    AS amostra_aghu,
       ise.ufe_ema_exa_sigla AS descricao
  FROM agh.ael_item_solicitacao_exames ise
 WHERE ise.soe_seq = :solicitacao_aghu
 ORDER BY ise.seqp;