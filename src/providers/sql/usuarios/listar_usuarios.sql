-- Usuários autorizados no SAP (perfil local), em ordem alfabética de login.
SELECT username, nome, role, active, created_at, updated_at
FROM authorized_users
ORDER BY username;
