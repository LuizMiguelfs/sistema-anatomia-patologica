-- Linha do tempo de um recurso (ex.: caso 123, escrito como tipo e código) em uma categoria, com paginação.
-- recurso   -> recurso exato
-- categoria -> categoria exibida no histórico (NEGOCIO_CLINICO)
-- O IP de origem não é selecionado: o histórico é aberto a qualquer usuário autenticado.
SELECT id, created_at, usuario, categoria, acao, recurso, dados_anteriores, dados_novos
FROM audit_logs
WHERE recurso = :recurso
  AND categoria = :categoria
ORDER BY created_at DESC, id DESC
LIMIT :limite OFFSET :offset;
