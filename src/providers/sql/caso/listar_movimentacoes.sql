SELECT id, caso_id, tipo, etapa_origem, etapa_destino, motivo, usuario, criado_em
  FROM caso_movimentacoes
 WHERE caso_id = :caso_id
 ORDER BY criado_em, id;