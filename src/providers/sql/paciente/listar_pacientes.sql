-- Lista pacientes do AGHU com busca opcional e paginação.
-- :termo   -> texto da busca (NULL = sem filtro); numérico busca pelo código
-- :padrao  -> padrão ILIKE para o nome (ex.: '%MARIA%')
-- :limite / :offset -> paginação
SELECT codigo, nome, dt_nascimento, sexo, cor, nome_mae, nome_pai
FROM agh.aip_pacientes
WHERE CAST(:termo AS TEXT) IS NULL
   OR nome ILIKE CAST(:padrao AS TEXT)
   OR CAST(codigo AS TEXT) = CAST(:termo AS TEXT)
ORDER BY nome, codigo
LIMIT :limite OFFSET :offset;
