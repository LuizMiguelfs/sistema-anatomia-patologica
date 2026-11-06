-- ATENÇÃO: o AGHU é SOMENTE LEITURA (RNF005). Esta query só é executada quando
-- PACIENTE_POSTGRES_ESCRITA=true (ex.: Postgres de desenvolvimento).
UPDATE agh.aip_pacientes
SET nome = :nome,
    dt_nascimento = CAST(:dt_nascimento AS DATE),
    sexo = :sexo,
    cor = :cor,
    nome_mae = :nome_mae,
    nome_pai = :nome_pai
WHERE codigo = :codigo
RETURNING codigo, nome, dt_nascimento, sexo, cor, nome_mae, nome_pai;
