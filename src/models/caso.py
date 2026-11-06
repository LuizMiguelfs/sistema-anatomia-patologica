"""
Modelos SQLAlchemy do módulo de Casos (banco local da aplicação)
=================================================================
Espelham a migração `20261105_casos_fluxo`. O acesso aos dados é feito por SQL nativo
(`src/providers/sql/caso/`); os modelos registram as tabelas no metadata (create_all em
desenvolvimento e referência para o Alembic). Sem exclusão física: `ativo` faz o soft delete.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import expression

from ..resources.database import Base


class Caso(Base):
    """Caso = uma solicitação do AGHU acompanhada pelo SAP (identificador SIGLA-NNNN/AA)."""

    __tablename__ = "casos"
    __table_args__ = (
        Index("ix_casos_paciente_nome", "paciente_nome"),
        Index("ix_casos_etapa_status", "etapa_atual", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    identificador_interno = Column(String(40), nullable=False, unique=True)
    solicitacao_aghu = Column(String(20), nullable=False, unique=True)
    paciente_codigo_aghu = Column(String(20), nullable=False)
    paciente_nome = Column(String(200), nullable=False)
    prontuario_aghu = Column(String(20))
    tipo_exame = Column(String(3), nullable=False)
    etapa_atual = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False)
    criado_por = Column(String(100), nullable=False)
    criado_em = Column(String(40), nullable=False)
    atualizado_em = Column(String(40), nullable=False)
    ativo = Column(Boolean, nullable=False, server_default=expression.true())


class CasoAmostra(Base):
    """Amostra do AGHU vinculada ao caso (sem registro órfão, RF004)."""

    __tablename__ = "caso_amostras"
    __table_args__ = (UniqueConstraint("caso_id", "amostra_aghu"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    caso_id = Column(Integer, ForeignKey("casos.id"), nullable=False)
    amostra_aghu = Column(String(20), nullable=False)
    descricao = Column(String(200))


class CasoMovimentacao(Base):
    """Movimentação do caso; append-only, a aplicação nunca altera nem apaga (RNF006)."""

    __tablename__ = "caso_movimentacoes"
    __table_args__ = (Index("ix_caso_mov_caso", "caso_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    caso_id = Column(Integer, ForeignKey("casos.id"), nullable=False)
    tipo = Column(String(20), nullable=False)
    etapa_origem = Column(String(30))
    etapa_destino = Column(String(30))
    motivo = Column(String(500))
    usuario = Column(String(100), nullable=False)
    criado_em = Column(String(40), nullable=False)


class CasoInconformidade(Base):
    """Inconformidade do caso (RF020); aberta impede o avanço (RF019)."""

    __tablename__ = "caso_inconformidades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caso_id = Column(Integer, ForeignKey("casos.id"), nullable=False)
    motivo = Column(String(500), nullable=False)
    situacao = Column(String(20), nullable=False, server_default="ABERTA")
    resolucao = Column(String(500))
    criado_por = Column(String(100), nullable=False)
    criado_em = Column(String(40), nullable=False)
    resolvido_em = Column(String(40))


class FluxoTransicao(Base):
    """Transição permitida por tipo de exame: o fluxo fica em dados, não em código (RF005/RNF011)."""

    __tablename__ = "fluxo_transicoes"
    __table_args__ = (UniqueConstraint("tipo_exame", "etapa_origem", "etapa_destino", "tipo"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_exame = Column(String(3), nullable=False)
    etapa_origem = Column(String(30), nullable=False)
    etapa_destino = Column(String(30), nullable=False)
    tipo = Column(String(20), nullable=False)  # AVANCO | ENCAMINHAMENTO
    ativo = Column(Boolean, nullable=False, server_default=expression.true())


class CasoSequencia(Base):
    """Último número do identificador interno usado por sigla e ano."""

    __tablename__ = "caso_sequencias"

    sigla = Column(String(3), primary_key=True)
    ano = Column(Integer, primary_key=True)
    ultimo = Column(Integer, nullable=False)
