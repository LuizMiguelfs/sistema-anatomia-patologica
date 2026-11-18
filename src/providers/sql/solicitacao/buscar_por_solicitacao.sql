SELECT id, identificador_interno
  FROM solicitacoes_exame
 WHERE solicitacao_aghu = :solicitacao_aghu
   AND ativo = 1;