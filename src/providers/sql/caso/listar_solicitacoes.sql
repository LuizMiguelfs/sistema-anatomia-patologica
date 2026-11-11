-- Solicitações de Exames: "Não retirados" (urgentes no topo, recebimento mais antigo primeiro)
-- e "Retirados" (retirada mais recente primeiro). Nome e prontuário saem cifrados.
SELECT c.id, c.identificador_interno, c.solicitacao_aghu, c.paciente_nome, c.prontuario_aghu,
       c.tipo_exame, c.etapa_atual, c.status, c.urgente, c.criado_em, c.retirado_em, c.retirado_por,
       (SELECT COUNT(*) FROM caso_amostras a WHERE a.caso_id = c.id) AS qtd_amostras,
       (SELECT GROUP_CONCAT(COALESCE(a.descricao, 'Amostra ' || a.amostra_aghu), '; ')
          FROM caso_amostras a WHERE a.caso_id = c.id) AS descricao_amostras
  FROM casos c
 WHERE c.ativo = 1
   AND (   (:situacao = 'NAO_RETIRADO' AND c.retirado_em IS NULL AND c.etapa_atual = 'RECEPCAO' AND c.status <> 'ARQUIVADO')
        OR (:situacao = 'RETIRADO' AND c.retirado_em IS NOT NULL))
   AND (:tipo_exame IS NULL OR c.tipo_exame = :tipo_exame)
   AND (:de  IS NULL OR substr(CASE WHEN :situacao = 'RETIRADO' THEN c.retirado_em ELSE c.criado_em END, 1, 10) >= :de)
   AND (:ate IS NULL OR substr(CASE WHEN :situacao = 'RETIRADO' THEN c.retirado_em ELSE c.criado_em END, 1, 10) <= :ate)
   AND (:busca IS NULL
        OR c.solicitacao_aghu = :busca
        OR c.identificador_interno = :busca_identificador
        OR c.prontuario_indice = :busca_prontuario)
 ORDER BY CASE WHEN :situacao = 'NAO_RETIRADO' THEN c.urgente END DESC,
          CASE WHEN :situacao = 'NAO_RETIRADO' THEN c.criado_em END ASC,
          CASE WHEN :situacao = 'RETIRADO' THEN c.retirado_em END DESC,
          c.id
 LIMIT :limite OFFSET :deslocamento;
