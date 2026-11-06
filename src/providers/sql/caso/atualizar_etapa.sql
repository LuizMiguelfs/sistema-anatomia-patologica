UPDATE casos
   SET etapa_atual = :etapa_atual,
       status = :status,
       atualizado_em = :agora
 WHERE id = :caso_id
   AND ativo = 1;