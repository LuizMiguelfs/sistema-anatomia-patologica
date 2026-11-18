-- Grava o formulário da fase (um por solicitação e fase): cria ou substitui o conteúdo.
-- O histórico do que mudou fica em audit_logs (antes/depois), na mesma transação.
INSERT INTO solicitacao_fases (solicitacao_id, etapa, dados, situacao, salvo_por, salvo_em, concluido_por, concluido_em)
VALUES (:solicitacao_id, :etapa, :dados, :situacao, :usuario, :agora, :concluido_por, :concluido_em)
ON CONFLICT (solicitacao_id, etapa) DO UPDATE
   SET dados = excluded.dados,
       situacao = excluded.situacao,
       salvo_por = excluded.salvo_por,
       salvo_em = excluded.salvo_em,
       concluido_por = excluded.concluido_por,
       concluido_em = excluded.concluido_em;
