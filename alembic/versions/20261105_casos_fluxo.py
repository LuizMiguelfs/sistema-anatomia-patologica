"""Módulo de Casos: casos, amostras, movimentações, inconformidades e fluxo configurável.

Revision ID: 20261105_casos_fluxo
Revises: 8a2efbe37bb6
"""
import sqlalchemy as sa
from alembic import op

revision = "20261105_casos_fluxo"
down_revision = down_revision = "8a2efbe37bb6"
branch_labels = None
depends_on = None

ESPINHA_HP = [("RECEPCAO", "MACROSCOPIA"), ("MACROSCOPIA", "PROCESSAMENTO"),
              ("PROCESSAMENTO", "MICROSCOPIA"), ("MICROSCOPIA", "ARQUIVO")]
ESPINHA_CITO = [("RECEPCAO", "PROCESSAMENTO"), ("PROCESSAMENTO", "MICROSCOPIA"), ("MICROSCOPIA", "ARQUIVO")]
ESPINHA_CO = [("RECEPCAO", "CONGELACAO"), ("CONGELACAO", "ARQUIVO")]  # ponto em aberto: CO e HP seguinte
DESVIOS_MICROSCOPIA = ["RECEPCAO", "PROCESSAMENTO", "IHQ", "REDE_EXTERNA"]  # tabela 4.3 (02-requisitos)


def _seed():
    linhas = []
    def add(tipo_exame, par, tipo):
        linhas.append({"tipo_exame": tipo_exame, "etapa_origem": par[0], "etapa_destino": par[1], "tipo": tipo, "ativo": True})
    for tipo_exame, espinha in (("HP", ESPINHA_HP), ("CG", ESPINHA_CITO), ("CCV", ESPINHA_CITO), ("CO", ESPINHA_CO)):
        add(tipo_exame, ("INICIO", "RECEPCAO"), "AVANCO")
        for par in espinha:
            add(tipo_exame, par, "AVANCO")
    for tipo_exame in ("HP", "CG", "CCV"):
        for destino in DESVIOS_MICROSCOPIA:
            add(tipo_exame, ("MICROSCOPIA", destino), "ENCAMINHAMENTO")
    add("HP", ("MACROSCOPIA", "RECEPCAO"), "ENCAMINHAMENTO")
    add("HP", ("MICROSCOPIA", "MACROSCOPIA"), "ENCAMINHAMENTO")  # revisão da peça: só HP
    return linhas


def upgrade() -> None:
    casos = op.create_table(
        "casos",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("identificador_interno", sa.String(40), nullable=False, unique=True),
        sa.Column("solicitacao_aghu", sa.String(20), nullable=False, unique=True),
        sa.Column("paciente_codigo_aghu", sa.String(20), nullable=False),
        sa.Column("paciente_nome", sa.String(200), nullable=False),
        sa.Column("prontuario_aghu", sa.String(20)),
        sa.Column("tipo_exame", sa.String(3), nullable=False),
        sa.Column("etapa_atual", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("criado_por", sa.String(100), nullable=False),
        sa.Column("criado_em", sa.String(40), nullable=False),
        sa.Column("atualizado_em", sa.String(40), nullable=False),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),  # soft delete
    )
    op.create_index("ix_casos_paciente_nome", "casos", ["paciente_nome"])
    op.create_index("ix_casos_etapa_status", "casos", ["etapa_atual", "status"])

    op.create_table(
        "caso_amostras",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("caso_id", sa.Integer, sa.ForeignKey("casos.id"), nullable=False),  # sem registro órfão (RF004)
        sa.Column("amostra_aghu", sa.String(20), nullable=False),
        sa.Column("descricao", sa.String(200)),
        sa.UniqueConstraint("caso_id", "amostra_aghu"),
    )
    op.create_table(
        "caso_movimentacoes",  # append-only: a aplicação nunca faz UPDATE/DELETE (RNF006)
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("caso_id", sa.Integer, sa.ForeignKey("casos.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("etapa_origem", sa.String(30)),
        sa.Column("etapa_destino", sa.String(30)),
        sa.Column("motivo", sa.String(500)),
        sa.Column("usuario", sa.String(100), nullable=False),
        sa.Column("criado_em", sa.String(40), nullable=False),
    )
    op.create_index("ix_caso_mov_caso", "caso_movimentacoes", ["caso_id"])
    op.create_table(
        "caso_inconformidades",  # compartilhada com UC016 (RF020); aqui só a leitura de pendências
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("caso_id", sa.Integer, sa.ForeignKey("casos.id"), nullable=False),
        sa.Column("motivo", sa.String(500), nullable=False),
        sa.Column("situacao", sa.String(20), nullable=False, server_default="ABERTA"),
        sa.Column("resolucao", sa.String(500)),
        sa.Column("criado_por", sa.String(100), nullable=False),
        sa.Column("criado_em", sa.String(40), nullable=False),
        sa.Column("resolvido_em", sa.String(40)),
    )
    fluxo = op.create_table(
        "fluxo_transicoes",  # fluxo por tipo de exame em dados, não em código (RF005/RNF011)
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tipo_exame", sa.String(3), nullable=False),
        sa.Column("etapa_origem", sa.String(30), nullable=False),
        sa.Column("etapa_destino", sa.String(30), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),  # AVANCO | ENCAMINHAMENTO
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tipo_exame", "etapa_origem", "etapa_destino", "tipo"),
    )
    op.bulk_insert(fluxo, _seed())


def downgrade() -> None:
    for tabela in ("fluxo_transicoes", "caso_inconformidades", "caso_movimentacoes", "caso_amostras", "casos"):
        op.drop_table(tabela)