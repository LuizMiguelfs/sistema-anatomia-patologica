-- Lista registros da trilha de auditoria com filtros opcionais e paginação.
-- Parâmetros NULL desativam o filtro correspondente.
-- usuario          -> login exato (comparação sem diferenciar maiúsculas/minúsculas)
-- categoria        -> SEGURANCA | NEGOCIO_CLINICO | CONFIGURACAO
-- acao             -> ação exata (ex.: CRIAR_PACIENTE)
-- recurso          -> recurso exato (ex.: paciente 123, escrito como tipo e código)
-- recurso_prefixo  -> padrão LIKE já escapado (ex.: 'paciente:%'), escape '\'
-- inicio / fim    -> intervalo UTC [inicio, fim) no formato 'AAAA-MM-DD HH.MM.SS.ffffff' (com dois-pontos nas horas)
-- limite / offset -> paginação
SELECT id, created_at, usuario, categoria, acao, recurso, dados_anteriores, dados_novos, ip_origem
FROM audit_logs
WHERE (:usuario IS NULL OR lower(usuario) = lower(:usuario))
  AND (:categoria IS NULL OR categoria = :categoria)
  AND (:acao IS NULL OR acao = :acao)
  AND (:recurso IS NULL OR recurso = :recurso)
  AND (:recurso_prefixo IS NULL OR recurso LIKE :recurso_prefixo ESCAPE '\')
  AND (:inicio IS NULL OR created_at >= :inicio)
  AND (:fim IS NULL OR created_at < :fim)
ORDER BY created_at DESC, id DESC
LIMIT :limite OFFSET :offset;
