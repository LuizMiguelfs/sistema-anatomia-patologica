"""Auditoria: triggers que bloqueiam UPDATE/DELETE em audit_logs (RNF006).

Revision ID: c7a1d2e3f405
Revises: 4b1f20261103
A aplicação também instala os triggers na inicialização (idempotente, IF NOT EXISTS);
esta revisão garante a proteção em bancos preparados apenas pelo Alembic.
"""
from alembic import op

from src.models.audit_log import instalar_protecao_auditoria

revision = "c7a1d2e3f405"
down_revision = "4b1f20261103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria os triggers de imutabilidade da trilha de auditoria (somente SQLite)."""
    instalar_protecao_auditoria(op.get_bind())


def downgrade() -> None:
    """Remover a proteção da trilha não é permitido."""
    raise RuntimeError("Downgrade desabilitado: a trilha de auditoria é imutável (RNF006)")
