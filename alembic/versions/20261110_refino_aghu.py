"""Metadados de sincronização do snapshot do AGHU no caso local.

Revision ID: 20261110_refino_aghu
Revises: 20261105_casos_fluxo
"""
from alembic import op
import sqlalchemy as sa

revision = "20261110_refino_aghu"
down_revision = "20261105_casos_fluxo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("casos", sa.Column("ultima_sincronizacao_aghu", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("casos", "ultima_sincronizacao_aghu")
