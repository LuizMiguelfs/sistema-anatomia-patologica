SELECT id, solicitacao_id, tipo, etapa_origem, etapa_destino, motivo, usuario, criado_em
  FROM solicitacao_movimentacoes
 WHERE solicitacao_id = :solicitacao_id
 ORDER BY criado_em, id;