-- Aguardando complementação: solicitações encaminhadas a outra etapa para processamento
-- complementar (IHQ, recorte, coloração especial, revisão da macroscopia, Rede Externa) que
-- ainda não voltaram à etapa de origem. Mesma regra de "em desvio" do controller
-- (ultima_movimentacao_desvio.sql): o último encaminhamento/retorno é um ENCAMINHAMENTO
-- para a etapa em que a solicitação está agora. Só a contagem sai daqui.
SELECT COUNT(*) AS total
  FROM solicitacoes_exame c
 WHERE c.ativo = 1
   AND c.status <> 'ARQUIVADO'
   AND (SELECT m.tipo || '|' || COALESCE(m.etapa_destino, '')
          FROM solicitacao_movimentacoes m
         WHERE m.solicitacao_id = c.id
           AND m.tipo IN ('ENCAMINHAMENTO', 'RETORNO')
         ORDER BY m.id DESC
         LIMIT 1) = 'ENCAMINHAMENTO|' || c.etapa_atual;
