SELECT id, solicitacao_id, etapa, dados, situacao, salvo_por, salvo_em, concluido_por, concluido_em
  FROM solicitacao_fases
 WHERE solicitacao_id = :solicitacao_id AND etapa = :etapa;
