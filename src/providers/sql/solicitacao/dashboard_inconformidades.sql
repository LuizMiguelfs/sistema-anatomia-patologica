SELECT COUNT(*) AS total
  FROM solicitacao_inconformidades i
  JOIN solicitacoes_exame c ON c.id = i.solicitacao_id
 WHERE c.ativo = 1 AND i.situacao = 'ABERTA';
