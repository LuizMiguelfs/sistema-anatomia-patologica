"""SAP auth: usuário autorizado e reparo não destrutivo do esquema legado.

Revision ID: 4b1f20261103
Revises: 8a2efbe37bb6
Atenção: a revisão legada 8a2efbe37bb6 apaga `refresh_tokens`;
faça backup antes de rodar qualquer migração desse histórico.
"""
from alembic import op
import sqlalchemy as sa

revision = "4b1f20261103"
down_revision = "8a2efbe37bb6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria (se faltarem) refresh_tokens, authorized_users e audit_logs, sem apagar dados."""
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens", sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(128), nullable=False),
            sa.Column("token", sa.String(64), nullable=False, unique=True),
            sa.Column("groups", sa.JSON(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
        op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)
    else:
        columns = {col["name"] for col in inspector.get_columns("refresh_tokens")}
        if "groups" not in columns:
            op.add_column("refresh_tokens", sa.Column("groups", sa.JSON(), nullable=True))
    if "authorized_users" not in tables:
        op.create_table(
            "authorized_users", sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(128), nullable=False, unique=True),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_authorized_users_username", "authorized_users", ["username"], unique=True)
    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs", sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("usuario", sa.String(), nullable=False),
            sa.Column("categoria", sa.String(), nullable=False),
            sa.Column("acao", sa.String(), nullable=False),
            sa.Column("recurso", sa.String(), nullable=False),
            sa.Column("dados_anteriores", sa.Text()),
            sa.Column("dados_novos", sa.Text()),
            sa.Column("ip_origem", sa.String()),
        )
        for col in ("usuario", "categoria", "acao", "recurso"):
            op.create_index(f"ix_audit_logs_{col}", "audit_logs", [col])


def downgrade() -> None:
    """Downgrade destrutivo desabilitado (retenção do histórico e das sessões)."""
    raise RuntimeError("Downgrade destrutivo desabilitado: retenção obrigatória do histórico e sessões")
