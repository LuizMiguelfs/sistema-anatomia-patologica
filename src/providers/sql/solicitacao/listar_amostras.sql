SELECT id, solicitacao_id, amostra_aghu, descricao
  FROM solicitacao_amostras
 WHERE solicitacao_id = :solicitacao_id
 ORDER BY id;