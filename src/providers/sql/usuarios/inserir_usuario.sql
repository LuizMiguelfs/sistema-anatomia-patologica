-- Inclusão de usuário autorizado: entra ativo, com o perfil escolhido pela Chefia.
INSERT INTO authorized_users (username, nome, role, active, created_at)
VALUES (:username, :nome, :role, 1, :agora);
