"""Sessões: exclusão lógica de refresh tokens (coluna deleted_at).

Revision ID: d3b8f1a2c6e7
Revises: c7a1d2e3f405
O SPEC proíbe exclusão física: renovação e logout passam a preencher `deleted_at`.
"""
from alembic import op
import sqlalchemy as sa

revision = "d3b8f1a2c6e7"
down_revision = "c7a1d2e3f405"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adiciona `refresh_tokens.deleted_at`, se ainda não existir."""
    colunas = {col["name"] for col in sa.inspect(op.get_bind()).get_columns("refresh_tokens")}
    if "deleted_at" not in colunas:
        op.add_column("refresh_tokens", sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remover a coluna perderia o registro de sessões revogadas."""
    raise RuntimeError("Downgrade desabilitado: retenção obrigatória do histórico de sessões")
