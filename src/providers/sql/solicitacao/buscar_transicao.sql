SELECT etapa_destino
  FROM fluxo_transicoes
 WHERE tipo_exame = :tipo_exame
   AND etapa_origem = :etapa_origem
   AND tipo = :tipo
   AND ativo = 1
 ORDER BY id;