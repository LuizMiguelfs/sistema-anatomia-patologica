-- Material retirado da recepção: encerra a etapa RECEPCAO e leva a solicitação à próxima fase.
UPDATE solicitacoes_exame
   SET retirado_em = :agora, retirado_por = :usuario,
       etapa_atual = :etapa_atual, status = :status, atualizado_em = :agora
 WHERE id = :solicitacao_id AND ativo = 1
   AND etapa_atual = 'RECEPCAO' AND retirado_em IS NULL AND status <> 'ARQUIVADO';
