-- Desfaz a retirada: a solicitação volta para "Não retirados" (etapa RECEPCAO).
UPDATE solicitacoes_exame
   SET retirado_em = NULL, retirado_por = NULL,
       etapa_atual = 'RECEPCAO', status = :status, atualizado_em = :agora
 WHERE id = :solicitacao_id AND ativo = 1;
