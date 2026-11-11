SELECT COUNT(*) AS total
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
        OR c.prontuario_indice = :busca_prontuario);
