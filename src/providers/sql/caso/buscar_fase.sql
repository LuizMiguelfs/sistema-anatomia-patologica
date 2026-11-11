SELECT id, caso_id, etapa, dados, situacao, salvo_por, salvo_em, concluido_por, concluido_em
  FROM caso_fases
 WHERE caso_id = :caso_id AND etapa = :etapa;
