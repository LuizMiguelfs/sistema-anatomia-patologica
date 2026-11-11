"""MVP: retirada da recepção, urgência, formulário por fase e fluxos de IHQ e Revisão de Lâmina.

Revision ID: 20261111_mvp_fases
Revises: 20261110_refino_aghu
"""
import sqlalchemy as sa
from alembic import op

revision = "20261111_mvp_fases"
down_revision = "20261110_refino_aghu"
branch_labels = None
depends_on = None

#: Novos fluxos do MVP (a solicitação de IHQ e a de Revisão de Lâmina têm fila própria).
NOVOS_FLUXOS = {
    "IHQ": [("INICIO", "RECEPCAO"), ("RECEPCAO", "IHQ"), ("IHQ", "ARQUIVO")],
    "RL": [("INICIO", "RECEPCAO"), ("RECEPCAO", "REVISAO"), ("REVISAO", "ARQUIVO")],
}


def upgrade() -> None:
    """Cria colunas de retirada/urgência, a tabela de formulários por fase e os novos fluxos."""
    bind = op.get_bind()
    colunas = {c["name"] for c in sa.inspect(bind).get_columns("casos")}
    with op.batch_alter_table("casos") as batch:
        if "urgente" not in colunas:
            batch.add_column(sa.Column("urgente", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "retirado_em" not in colunas:
            batch.add_column(sa.Column("retirado_em", sa.String(40), nullable=True))
        if "retirado_por" not in colunas:
            batch.add_column(sa.Column("retirado_por", sa.String(100), nullable=True))

    if "caso_fases" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "caso_fases",  # formulário de cada fase do setor (rascunho ou concluído)
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("caso_id", sa.Integer(), sa.ForeignKey("casos.id"), nullable=False),
            sa.Column("etapa", sa.String(30), nullable=False),
            sa.Column("dados", sa.Text(), nullable=False),
            sa.Column("situacao", sa.String(20), nullable=False),
            sa.Column("salvo_por", sa.String(100), nullable=False),
            sa.Column("salvo_em", sa.String(40), nullable=False),
            sa.Column("concluido_por", sa.String(100)),
            sa.Column("concluido_em", sa.String(40)),
            sa.UniqueConstraint("caso_id", "etapa"),
        )
        op.create_index("ix_caso_fases_etapa", "caso_fases", ["etapa", "situacao"])

    # Congelação é sempre urgente (decisão do setor).
    op.execute("UPDATE casos SET urgente = 1 WHERE tipo_exame = 'CO'")

    fluxo = sa.table(
        "fluxo_transicoes",
        sa.column("tipo_exame", sa.String), sa.column("etapa_origem", sa.String),
        sa.column("etapa_destino", sa.String), sa.column("tipo", sa.String), sa.column("ativo", sa.Boolean),
    )
    for tipo_exame, pares in NOVOS_FLUXOS.items():
        existe = bind.execute(
            sa.text("SELECT COUNT(*) FROM fluxo_transicoes WHERE tipo_exame = :t"), {"t": tipo_exame}
        ).scalar()
        if not existe:
            op.bulk_insert(fluxo, [
                {"tipo_exame": tipo_exame, "etapa_origem": o, "etapa_destino": d, "tipo": "AVANCO", "ativo": True}
                for o, d in pares
            ])


def downgrade() -> None:
    """Remove os fluxos novos, a tabela de formulários e as colunas do MVP."""
    op.execute("DELETE FROM fluxo_transicoes WHERE tipo_exame IN ('IHQ', 'RL')")
    op.drop_index("ix_caso_fases_etapa", table_name="caso_fases")
    op.drop_table("caso_fases")
    with op.batch_alter_table("casos") as batch:
        batch.drop_column("retirado_por")
        batch.drop_column("retirado_em")
        batch.drop_column("urgente")
