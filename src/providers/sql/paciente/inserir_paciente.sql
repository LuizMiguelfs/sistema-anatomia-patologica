-- ATENÇÃO: o AGHU é SOMENTE LEITURA (RNF005). Esta query só é executada quando
-- PACIENTE_POSTGRES_ESCRITA=true (ex.: Postgres de desenvolvimento).
-- O código é gerado pelo default/sequence da coluna `codigo` no banco.
INSERT INTO agh.aip_pacientes (nome, dt_nascimento, sexo, cor, nome_mae, nome_pai)
VALUES (:nome, CAST(:dt_nascimento AS DATE), :sexo, :cor, :nome_mae, :nome_pai)
RETURNING codigo, nome, dt_nascimento, sexo, cor, nome_mae, nome_pai;
