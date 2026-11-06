SELECT id, tipo, etapa_origem, etapa_destino
  FROM caso_movimentacoes
 WHERE caso_id = :caso_id
   AND tipo IN ('ENCAMINHAMENTO', 'RETORNO')
 ORDER BY id DESC
 LIMIT 1;