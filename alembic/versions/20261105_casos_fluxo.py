"""Módulo de Casos: casos, amostras, movimentações, inconformidades e fluxo configurável.

Revision ID: 20261105_casos_fluxo
Revises: e5a9c4d7b210
"""
import sqlalchemy as sa
from alembic import op

revision = "20261105_casos_fluxo"
down_revision = "e5a9c4d7b210"  # depois das migrações do main (head único)
branch_labels = None
depends_on = None

ESPINHA_HP = [("RECEPCAO", "MACROSCOPIA"), ("MACROSCOPIA", "PROCESSAMENTO"),
              ("PROCESSAMENTO", "MICROSCOPIA"), ("MICROSCOPIA", "ARQUIVO")]
ESPINHA_CITO = [("RECEPCAO", "PROCESSAMENTO"), ("PROCESSAMENTO", "MICROSCOPIA"), ("MICROSCOPIA", "ARQUIVO")]
ESPINHA_CO = [("RECEPCAO", "CONGELACAO"), ("CONGELACAO", "ARQUIVO")]  # ponto em aberto: CO e HP seguinte
DESVIOS_MICROSCOPIA = ["RECEPCAO", "PROCESSAMENTO", "IHQ", "REDE_EXTERNA"]  # tabela 4.3 (02-requisitos)


def _seed() -> list:
    """Fluxo inicial por tipo de exame (espinha dorsal + encaminhamentos da tabela 4.3)."""
    linhas = []
    def add(tipo_exame: str, par: tuple, tipo: str) -> None:
        """Acrescenta uma transição ativa."""
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
    """Cria as tabelas do módulo de casos que ainda não existem e semeia o fluxo, se vazio.

    Idempotente: em desenvolvimento o `create_all` da aplicação pode ter criado as tabelas antes.
    """
    bind = op.get_bind()
    existentes = set(sa.inspect(bind).get_table_names())

    if "casos" not in existentes:
        op.create_table(
            "casos",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("identificador_interno", sa.String(40), nullable=False, unique=True),
            sa.Column("solicitacao_aghu", sa.String(20), nullable=False, unique=True),
            sa.Column("paciente_codigo_aghu", sa.String(20), nullable=False),
            sa.Column("paciente_nome", sa.Text, nullable=False),  # cifrado (AES-256)
            sa.Column("prontuario_aghu", sa.Text),  # cifrado (AES-256)
            sa.Column("prontuario_indice", sa.String(64)),  # HMAC do prontuário, para busca exata
            sa.Column("tipo_exame", sa.String(3), nullable=False),
            sa.Column("etapa_atual", sa.String(30), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("criado_por", sa.String(100), nullable=False),
            sa.Column("criado_em", sa.String(40), nullable=False),
            sa.Column("atualizado_em", sa.String(40), nullable=False),
            sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),  # soft delete
        )
        op.create_index("ix_casos_prontuario_indice", "casos", ["prontuario_indice"])
    elif "prontuario_indice" not in {c["name"] for c in sa.inspect(bind).get_columns("casos")}:
        # Banco criado por uma versão anterior desta migração.
        op.add_column("casos", sa.Column("prontuario_indice", sa.String(64)))
        op.create_index("ix_casos_prontuario_indice", "casos", ["prontuario_indice"])
        op.create_index("ix_casos_etapa_status", "casos", ["etapa_atual", "status"])

    if "caso_amostras" not in existentes:
        op.create_table(
            "caso_amostras",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("caso_id", sa.Integer, sa.ForeignKey("casos.id"), nullable=False),  # sem órfão (RF004)
            sa.Column("amostra_aghu", sa.String(20), nullable=False),
            sa.Column("descricao", sa.String(200)),
            sa.UniqueConstraint("caso_id", "amostra_aghu"),
        )

    if "caso_movimentacoes" not in existentes:
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

    if "caso_inconformidades" not in existentes:
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

    if "fluxo_transicoes" not in existentes:
        op.create_table(
            "fluxo_transicoes",  # fluxo por tipo de exame em dados, não em código (RF005/RNF011)
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("tipo_exame", sa.String(3), nullable=False),
            sa.Column("etapa_origem", sa.String(30), nullable=False),
            sa.Column("etapa_destino", sa.String(30), nullable=False),
            sa.Column("tipo", sa.String(20), nullable=False),  # AVANCO | ENCAMINHAMENTO
            sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.UniqueConstraint("tipo_exame", "etapa_origem", "etapa_destino", "tipo"),
        )
    fluxo = sa.table(
        "fluxo_transicoes",
        sa.column("tipo_exame", sa.String), sa.column("etapa_origem", sa.String),
        sa.column("etapa_destino", sa.String), sa.column("tipo", sa.String), sa.column("ativo", sa.Boolean),
    )
    if not bind.execute(sa.text("SELECT COUNT(*) FROM fluxo_transicoes")).scalar():
        op.bulk_insert(fluxo, _seed())

    if "caso_sequencias" not in existentes:
        op.create_table(
            "caso_sequencias",  # numeração do identificador interno SIGLA-NNNN/AA, por sigla e por ano
            sa.Column("sigla", sa.String(3), primary_key=True),
            sa.Column("ano", sa.Integer, primary_key=True),
            sa.Column("ultimo", sa.Integer, nullable=False),
        )


def downgrade() -> None:
    """Sem downgrade destrutivo: apagar as tabelas perderia casos e histórico (sem exclusão física)."""
    raise RuntimeError("Downgrade desabilitado: retenção obrigatória dos casos e do histórico")