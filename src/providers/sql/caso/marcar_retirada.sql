-- Material retirado da recepção: encerra a etapa RECEPCAO e leva a solicitação à próxima fase.
UPDATE casos
   SET retirado_em = :agora, retirado_por = :usuario,
       etapa_atual = :etapa_atual, status = :status, atualizado_em = :agora
 WHERE id = :caso_id AND ativo = 1;
