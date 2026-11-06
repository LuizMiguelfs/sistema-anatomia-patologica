"""Gestão de usuários: nome de exibição do AD em authorized_users.

Revision ID: e5a9c4d7b210
Revises: d3b8f1a2c6e7
"""
from alembic import op
import sqlalchemy as sa

revision = "e5a9c4d7b210"
down_revision = "d3b8f1a2c6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adiciona `authorized_users.nome`, se ainda não existir."""
    colunas = {col["name"] for col in sa.inspect(op.get_bind()).get_columns("authorized_users")}
    if "nome" not in colunas:
        op.add_column("authorized_users", sa.Column("nome", sa.String(200), nullable=True))


def downgrade() -> None:
    """Sem downgrade destrutivo (retenção do cadastro de acesso)."""
    raise RuntimeError("Downgrade desabilitado: retenção obrigatória do cadastro de usuários")
