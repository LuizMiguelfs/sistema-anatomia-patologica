SELECT id, identificador_interno
  FROM casos
 WHERE solicitacao_aghu = :solicitacao_aghu
   AND ativo = 1;