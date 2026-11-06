SELECT COUNT(*) AS total
  FROM caso_inconformidades
 WHERE caso_id = :caso_id
   AND situacao = 'ABERTA';