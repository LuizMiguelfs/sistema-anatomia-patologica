-- Fila de uma fase: pendentes da fase (urgentes no topo, entrada mais antiga primeiro) e,
-- abaixo, as concluídas nos últimos dias, ainda editáveis (conclusão mais recente primeiro).
SELECT * FROM (
SELECT c.id, c.identificador_interno, c.solicitacao_aghu, c.paciente_nome, c.prontuario_aghu,
       c.tipo_exame, c.etapa_atual, c.status, c.urgente, c.criado_em,
       f.situacao AS situacao_fase, f.salvo_em, f.salvo_por, f.concluido_em, f.concluido_por,
       CASE WHEN c.etapa_atual = :etapa AND c.status <> 'ARQUIVADO' THEN 1 ELSE 0 END AS pendente,
       (SELECT MAX(m.criado_em) FROM caso_movimentacoes m
         WHERE m.caso_id = c.id AND m.etapa_destino = :etapa) AS entrou_em,
       (SELECT COUNT(*) FROM caso_amostras a WHERE a.caso_id = c.id) AS qtd_amostras,
       (SELECT GROUP_CONCAT(COALESCE(a.descricao, 'Amostra ' || a.amostra_aghu), '; ')
          FROM caso_amostras a WHERE a.caso_id = c.id) AS descricao_amostras
  FROM casos c
  LEFT JOIN caso_fases f ON f.caso_id = c.id AND f.etapa = :etapa
 WHERE c.ativo = 1
   AND (   (c.etapa_atual = :etapa AND c.status <> 'ARQUIVADO')
        OR (f.situacao = 'CONCLUIDA' AND f.concluido_em >= :concluidas_desde AND c.etapa_atual <> :etapa))
   AND (:tipo_exame IS NULL OR c.tipo_exame = :tipo_exame)
   AND (:busca IS NULL
        OR c.solicitacao_aghu = :busca
        OR c.identificador_interno = :busca_identificador
        OR c.prontuario_indice = :busca_prontuario)
)
 ORDER BY pendente DESC,
          CASE WHEN pendente = 1 THEN urgente END DESC,
          CASE WHEN pendente = 1 THEN entrou_em END ASC,
          concluido_em DESC,
          id
 LIMIT :limite OFFSET :deslocamento;
