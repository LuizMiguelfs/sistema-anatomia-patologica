SELECT id, caso_id, amostra_aghu, descricao
  FROM caso_amostras
 WHERE caso_id = :caso_id
 ORDER BY id;