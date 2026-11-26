SELECT solicitacao_id, fonte, referencia, liberado_em, liberado_por, arquivado_em, arquivado_por
FROM solicitacao_liberacoes
WHERE solicitacao_id = :solicitacao_id;
