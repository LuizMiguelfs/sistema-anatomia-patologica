"""T08: evento demonstrativo de liberação AGHU e arquivamento rastreável.

Revision ID: 20261125_thiago_laudos
Revises: 20261118_renomear_solicitacao
"""
import sqlalchemy as sa
from alembic import op

revision = "20261125_thiago_laudos"
down_revision = "20261118_renomear_solicitacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria armazenamento local de marcadores, sem modificar dados oficiais do AGHU."""
    if "solicitacao_liberacoes" in sa.inspect(op.get_bind()).get_table_names():
        return  # create_all pode tê-la criado durante desenvolvimento, sem dados antigos.
    op.create_table(
        "solicitacao_liberacoes",
        sa.Column("solicitacao_id", sa.Integer(), sa.ForeignKey("solicitacoes_exame.id"), primary_key=True),
        sa.Column("fonte", sa.String(30), nullable=False),
        sa.Column("referencia", sa.String(80), nullable=False),
        sa.Column("liberado_em", sa.String(40), nullable=False),
        sa.Column("liberado_por", sa.String(100), nullable=False),
        sa.Column("arquivado_em", sa.String(40), nullable=True),
        sa.Column("arquivado_por", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    """Reverte somente a tabela desta entrega; exige backup antes de aplicar."""
    op.drop_table("solicitacao_liberacoes")
