"""Non-destructive compatibility migration for refresh tokens.

Revision ID: 8a2efbe37bb6
Revises: df72b10ec0f3
"""
from alembic import op
import sqlalchemy as sa

revision = '8a2efbe37bb6'
down_revision = 'df72b10ec0f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Acrescenta refresh_tokens.groups se a tabela já existir (sem apagar nada)."""
    inspector = sa.inspect(op.get_bind())
    if 'refresh_tokens' not in inspector.get_table_names():
        # The following revision 4b1f20261103 creates the table with the final schema.
        return
    columns = {c['name'] for c in inspector.get_columns('refresh_tokens')}
    if 'groups' not in columns:
        op.add_column('refresh_tokens', sa.Column('groups', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade destrutivo desabilitado (preserva as sessões)."""
    raise RuntimeError('Downgrade destrutivo desabilitado para preservar sessões')
