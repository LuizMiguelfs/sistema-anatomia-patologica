SELECT etapa_destino
  FROM fluxo_transicoes
 WHERE tipo_exame = :tipo_exame
   AND etapa_origem = 'INICIO'
   AND tipo = 'AVANCO'
   AND ativo = 1
 LIMIT 1;