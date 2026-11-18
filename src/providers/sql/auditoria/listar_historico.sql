-- Linha do tempo de um recurso (ex.: solicitação 123, escrito como tipo e código) em uma categoria, com paginação.
-- recurso         -> recurso exato
-- recurso_legado  -> nome antigo do mesmo recurso (ex.: caso:123, antes da T4.1) ou NULL
-- categoria -> categoria exibida no histórico (NEGOCIO_CLINICO)
-- O IP de origem não é selecionado: o histórico é aberto a qualquer usuário autenticado.
SELECT id, created_at, usuario, categoria, acao, recurso, dados_anteriores, dados_novos
FROM audit_logs
WHERE (recurso = :recurso OR recurso = :recurso_legado)
  AND categoria = :categoria
ORDER BY created_at DESC, id DESC
LIMIT :limite OFFSET :offset;
