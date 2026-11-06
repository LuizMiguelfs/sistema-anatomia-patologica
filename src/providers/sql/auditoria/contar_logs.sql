-- Conta os registros da trilha de auditoria com os mesmos filtros de listar_logs.sql.
SELECT COUNT(*) AS total
FROM audit_logs
WHERE (:usuario IS NULL OR lower(usuario) = lower(:usuario))
  AND (:categoria IS NULL OR categoria = :categoria)
  AND (:acao IS NULL OR acao = :acao)
  AND (:recurso IS NULL OR recurso = :recurso)
  AND (:recurso_prefixo IS NULL OR recurso LIKE :recurso_prefixo ESCAPE '\')
  AND (:inicio IS NULL OR created_at >= :inicio)
  AND (:fim IS NULL OR created_at < :fim);
