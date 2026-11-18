"""Renomeia "caso" para "solicitação de exame" nas tabelas, colunas e índices (T4.1).

Só renomeia: nenhum dado é apagado, copiado ou alterado. A trilha de auditoria não muda
(é imutável); registros antigos continuam com o recurso "caso:<id>" e o histórico lê os dois.

Revision ID: 20261118_renomear_solicitacao
Revises: 20261111_mvp_fases
"""
import sqlalchemy as sa
from alembic import op

revision = "20261118_renomear_solicitacao"
down_revision = "20261111_mvp_fases"
branch_labels = None
depends_on = None

#: (nome antigo, nome novo) das tabelas.
TABELAS = [
    ("casos", "solicitacoes_exame"),
    ("caso_amostras", "solicitacao_amostras"),
    ("caso_movimentacoes", "solicitacao_movimentacoes"),
    ("caso_fases", "solicitacao_fases"),
    ("caso_inconformidades", "solicitacao_inconformidades"),
    ("caso_sequencias", "solicitacao_sequencias"),
]

#: Tabelas (já com o nome novo) cuja coluna de vínculo passa de caso_id para solicitacao_id.
COM_VINCULO = ["solicitacao_amostras", "solicitacao_movimentacoes", "solicitacao_fases", "solicitacao_inconformidades"]

#: (índice antigo, índice novo, tabela com nome novo, colunas).
INDICES = [
    ("ix_casos_prontuario_indice", "ix_solicitacoes_exame_prontuario_indice", "solicitacoes_exame", ["prontuario_indice"]),
    ("ix_casos_etapa_status", "ix_solicitacoes_exame_etapa_status", "solicitacoes_exame", ["etapa_atual", "status"]),
    ("ix_caso_mov_caso", "ix_solicitacao_mov_solicitacao", "solicitacao_movimentacoes", ["solicitacao_id"]),
    ("ix_caso_fases_etapa", "ix_solicitacao_fases_etapa", "solicitacao_fases", ["etapa", "situacao"]),
]


def _indices(tabela: str) -> set:
    """Nomes dos índices existentes na tabela."""
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(tabela)}


def _renomear_indices(de_para: list) -> None:
    """Troca o nome de cada índice que existir (SQLite não renomeia índice: recria)."""
    for antigo, novo, tabela, colunas in de_para:
        if antigo in _indices(tabela):
            op.drop_index(antigo, table_name=tabela)
            op.create_index(novo, tabela, colunas)


def upgrade() -> None:
    """Renomeia tabelas, a coluna caso_id e os índices; os dados ficam como estão."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    for antigo, novo in TABELAS:
        if antigo in existentes:
            op.rename_table(antigo, novo)  # o SQLite atualiza as chaves estrangeiras que apontam para ela
    for tabela in COM_VINCULO:
        op.execute(f"ALTER TABLE {tabela} RENAME COLUMN caso_id TO solicitacao_id")
    _renomear_indices(INDICES)


def downgrade() -> None:
    """Volta todos os nomes de "caso", na ordem inversa."""
    _renomear_indices([(novo, antigo, tabela, colunas) for antigo, novo, tabela, colunas in INDICES])
    for tabela in COM_VINCULO:
        op.execute(f"ALTER TABLE {tabela} RENAME COLUMN solicitacao_id TO caso_id")
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    for antigo, novo in reversed(TABELAS):
        if novo in existentes:
            op.rename_table(novo, antigo)
