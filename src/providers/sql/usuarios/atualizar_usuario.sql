-- Alteração de perfil e/ou situação. Não há exclusão: inativar mantém o registro.
UPDATE authorized_users
SET role = :role,
    active = :active,
    updated_at = :agora
WHERE username = :username;
