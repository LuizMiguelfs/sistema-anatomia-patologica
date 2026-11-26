UPDATE solicitacao_liberacoes
SET arquivado_em = :agora, arquivado_por = :usuario
WHERE solicitacao_id = :solicitacao_id AND arquivado_em IS NULL;
