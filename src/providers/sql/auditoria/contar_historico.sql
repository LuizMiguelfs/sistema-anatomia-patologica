-- Conta os registros do histórico de um recurso (mesmos filtros de listar_historico.sql).
SELECT COUNT(*) AS total
FROM audit_logs
WHERE recurso = :recurso
  AND categoria = :categoria;
