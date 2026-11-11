SELECT COUNT(*) AS total
  FROM caso_inconformidades i
  JOIN casos c ON c.id = i.caso_id
 WHERE c.ativo = 1 AND i.situacao = 'ABERTA';
