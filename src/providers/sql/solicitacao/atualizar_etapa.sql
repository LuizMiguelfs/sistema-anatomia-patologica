UPDATE solicitacoes_exame
   SET etapa_atual = :etapa_atual,
       status = :status,
       atualizado_em = :agora
 WHERE id = :solicitacao_id
   AND ativo = 1;