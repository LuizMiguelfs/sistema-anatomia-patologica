-- Fila de revisão: rascunhos nas fases com pré-laudo; não inclui solicitações já concluídas.
SELECT s.id, s.identificador_interno, s.solicitacao_aghu, s.paciente_nome, s.prontuario_aghu,
       s.tipo_exame, s.etapa_atual, s.urgente, f.dados, f.salvo_em, f.salvo_por,
       CASE WHEN COALESCE(TRIM(CAST(json_extract(f.dados, '$.pre_laudo') AS TEXT)),
                          TRIM(CAST(json_extract(f.dados, '$.analise_preliminar') AS TEXT)), '') = ''
            THEN 'RASCUNHO' ELSE 'EM_REVISAO' END AS situacao_revisao
FROM solicitacoes_exame s
JOIN solicitacao_fases f ON f.solicitacao_id = s.id AND f.etapa = s.etapa_atual
WHERE s.ativo = 1 AND s.status <> 'ARQUIVADO' AND f.situacao = 'RASCUNHO'
  AND s.etapa_atual IN ('MICROSCOPIA', 'REVISAO', 'CONGELACAO')
ORDER BY s.urgente DESC, f.salvo_em ASC, s.id ASC
LIMIT :limite OFFSET :deslocamento;
