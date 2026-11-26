-- Histórico clínico local já validado nas fases; não busca nem cria documento oficial no AGHU.
SELECT etapa, dados, situacao, salvo_por, salvo_em, concluido_por, concluido_em
FROM solicitacao_fases
WHERE solicitacao_id = :solicitacao_id AND situacao = 'CONCLUIDA'
ORDER BY concluido_em, etapa;
