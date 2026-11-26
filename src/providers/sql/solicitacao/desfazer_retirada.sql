-- Desfaz a retirada: a solicitação volta para "Não retirados" (etapa RECEPCAO).
UPDATE solicitacoes_exame
   SET retirado_em = NULL, retirado_por = NULL,
       etapa_atual = 'RECEPCAO', status = :status, atualizado_em = :agora
 WHERE id = :solicitacao_id AND ativo = 1 AND retirado_em IS NOT NULL
   AND status <> 'ARQUIVADO'
   AND EXISTS (
       SELECT 1 FROM fluxo_transicoes ft
       WHERE ft.tipo_exame = solicitacoes_exame.tipo_exame
         AND ft.etapa_origem = 'RECEPCAO'
         AND ft.etapa_destino = solicitacoes_exame.etapa_atual
         AND ft.tipo = 'AVANCO' AND ft.ativo = 1
   )
   AND NOT EXISTS (
       SELECT 1 FROM solicitacao_fases sf
       WHERE sf.solicitacao_id = solicitacoes_exame.id
         AND sf.etapa = solicitacoes_exame.etapa_atual
   );
