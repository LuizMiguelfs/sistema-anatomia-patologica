"""
Modelos SQLAlchemy do módulo de Solicitações (banco local da aplicação)
=================================================================
Espelham as migrações `20261105_casos_fluxo` (criação) e `20261118_renomear_solicitacao` (nomes atuais). O acesso aos dados é feito por SQL nativo
(`src/providers/sql/solicitacao/`); os modelos registram as tabelas no metadata (create_all em
desenvolvimento e referência para o Alembic). Sem exclusão física: `ativo` faz o soft delete.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import expression

from ..resources.database import Base


class SolicitacaoExame(Base):
    """
    Solicitação de exame do AGHU acompanhada pelo SAP (identificador SIGLA-NNNN/AA).
    Nome e prontuário do paciente ficam cifrados; o código do paciente no AGHU é a chave técnica
    de vínculo com a fonte e fica em claro, como o código usado nos recursos da auditoria.
    """

    __tablename__ = "solicitacoes_exame"
    __table_args__ = (
        Index("ix_solicitacoes_exame_prontuario_indice", "prontuario_indice"),
        Index("ix_solicitacoes_exame_etapa_status", "etapa_atual", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    identificador_interno = Column(String(40), nullable=False, unique=True)
    solicitacao_aghu = Column(String(20), nullable=False, unique=True)
    paciente_codigo_aghu = Column(String(20), nullable=False)
    paciente_nome = Column(Text, nullable=False)  # cifrado com AES-256 (SPEC.md)
    prontuario_aghu = Column(Text)  # cifrado com AES-256 (SPEC.md)
    prontuario_indice = Column(String(64))  # HMAC-SHA256 do prontuário normalizado, só para busca exata
    tipo_exame = Column(String(3), nullable=False)
    ultima_sincronizacao_aghu = Column(String(40))  # UTC; sem editar a fonte
    etapa_atual = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False)
    urgente = Column(Boolean, nullable=False, server_default=expression.false())  # CO é sempre urgente
    retirado_em = Column(String(40))  # UTC; material retirado da recepção (encerra a etapa RECEPCAO)
    retirado_por = Column(String(100))
    criado_por = Column(String(100), nullable=False)
    criado_em = Column(String(40), nullable=False)
    atualizado_em = Column(String(40), nullable=False)
    ativo = Column(Boolean, nullable=False, server_default=expression.true())


class SolicitacaoAmostra(Base):
    """Amostra do AGHU vinculada à solicitação (sem registro órfão, RF004)."""

    __tablename__ = "solicitacao_amostras"
    __table_args__ = (UniqueConstraint("solicitacao_id", "amostra_aghu"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    solicitacao_id = Column(Integer, ForeignKey("solicitacoes_exame.id"), nullable=False)
    amostra_aghu = Column(String(20), nullable=False)
    descricao = Column(String(200))


class SolicitacaoMovimentacao(Base):
    """Movimentação da solicitação; append-only, a aplicação nunca altera nem apaga (RNF006)."""

    __tablename__ = "solicitacao_movimentacoes"
    __table_args__ = (Index("ix_solicitacao_mov_solicitacao", "solicitacao_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    solicitacao_id = Column(Integer, ForeignKey("solicitacoes_exame.id"), nullable=False)
    tipo = Column(String(20), nullable=False)
    etapa_origem = Column(String(30))
    etapa_destino = Column(String(30))
    motivo = Column(String(500))
    usuario = Column(String(100), nullable=False)
    criado_em = Column(String(40), nullable=False)


class SolicitacaoInconformidade(Base):
    """Inconformidade da solicitação (RF020); aberta impede o avanço (RF019)."""

    __tablename__ = "solicitacao_inconformidades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    solicitacao_id = Column(Integer, ForeignKey("solicitacoes_exame.id"), nullable=False)
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


class SolicitacaoSequencia(Base):
    """Último número do identificador interno usado por sigla e ano."""

    __tablename__ = "solicitacao_sequencias"

    sigla = Column(String(3), primary_key=True)
    ano = Column(Integer, primary_key=True)
    ultimo = Column(Integer, nullable=False)


class SolicitacaoFase(Base):
    """Formulário de uma fase do setor para o solicitacao: rascunho (Salvar) ou concluído (Concluído)."""

    __tablename__ = "solicitacao_fases"
    __table_args__ = (
        UniqueConstraint("solicitacao_id", "etapa"),
        Index("ix_solicitacao_fases_etapa", "etapa", "situacao"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    solicitacao_id = Column(Integer, ForeignKey("solicitacoes_exame.id"), nullable=False)
    etapa = Column(String(30), nullable=False)
    dados = Column(Text, nullable=False)  # JSON com os campos do formulário da fase
    situacao = Column(String(20), nullable=False)  # RASCUNHO | CONCLUIDA
    salvo_por = Column(String(100), nullable=False)
    salvo_em = Column(String(40), nullable=False)
    concluido_por = Column(String(100))
    concluido_em = Column(String(40))
