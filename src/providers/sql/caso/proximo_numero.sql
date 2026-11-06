-- Reserva o próximo número do identificador interno (SIGLA-NNNN/AA) da sigla no ano.
-- A numeração é separada por sigla e recomeça a cada ano. Executada na transação de abertura do caso.
INSERT INTO caso_sequencias (sigla, ano, ultimo)
VALUES (:sigla, :ano, 1)
ON CONFLICT (sigla, ano) DO UPDATE SET ultimo = ultimo + 1
RETURNING ultimo;
