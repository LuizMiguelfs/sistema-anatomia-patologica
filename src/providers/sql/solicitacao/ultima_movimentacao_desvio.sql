SELECT id, tipo, etapa_origem, etapa_destino
  FROM solicitacao_movimentacoes
 WHERE solicitacao_id = :solicitacao_id
   AND tipo IN ('ENCAMINHAMENTO', 'RETORNO')
 ORDER BY id DESC
 LIMIT 1;