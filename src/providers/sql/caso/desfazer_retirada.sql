-- Desfaz a retirada: a solicitação volta para "Não retirados" (etapa RECEPCAO).
UPDATE casos
   SET retirado_em = NULL, retirado_por = NULL,
       etapa_atual = 'RECEPCAO', status = :status, atualizado_em = :agora
 WHERE id = :caso_id AND ativo = 1;
