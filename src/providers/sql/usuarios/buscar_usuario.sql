-- Um usuário autorizado pelo login de rede (normalizado).
SELECT username, nome, role, active, created_at, updated_at
FROM authorized_users
WHERE username = :username;
