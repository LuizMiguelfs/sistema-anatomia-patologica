SELECT COUNT(*) AS total
  FROM solicitacao_inconformidades
 WHERE solicitacao_id = :solicitacao_id
   AND situacao = 'ABERTA';