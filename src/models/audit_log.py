"""
Modelo SQLAlchemy de Auditoria e Trilha de Mudanças (Audit Log)
================================================================
Registra de forma estruturada e imutável as ações de mutação (criação, alteração, exclusão,
troca de privilégios) realizadas por usuários no sistema.

Imutabilidade (RNF006): registros de auditoria nunca são alterados nem apagados.
- Pelo ORM: tentativas de UPDATE/DELETE de um AuditLog levantam AuditLogImutavelError.
- Pelo banco (SQLite): triggers bloqueiam UPDATE/DELETE mesmo em SQL direto.
  Ver `instalar_protecao_auditoria`, chamada na inicialização da aplicação.
"""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, Integer, String, Text, DateTime, event, text
from ..resources.database import Base

#: Categorias obrigatórias definidas pelo framework (docs/AUDITORIA_E_LOGS.md).
CATEGORIAS_AUDITORIA = ("SEGURANCA", "NEGOCIO_CLINICO", "CONFIGURACAO")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    usuario = Column(String, nullable=False, index=True)
    categoria = Column(String, nullable=False, index=True)  # SEGURANCA, NEGOCIO_CLINICO, CONFIGURACAO
    acao = Column(String, nullable=False, index=True)       # ex: ALTERAR_PERFIL, CRIAR_PACIENTE
    recurso = Column(String, nullable=False, index=True)    # ex: usuario:joao.silva, paciente:123
    dados_anteriores = Column(Text, nullable=True)          # JSON serializado do estado BEFORE
    dados_novos = Column(Text, nullable=True)               # JSON serializado do estado AFTER
    ip_origem = Column(String, nullable=True)

    def __repr__(self) -> str:
        """Representação curta do registro, para depuração."""
        return f"<AuditLog id={self.id} usuario={self.usuario} acao={self.acao} recurso={self.recurso}>"


class AuditLogImutavelError(RuntimeError):
    """Tentativa de alterar ou apagar um registro de auditoria."""


@event.listens_for(AuditLog, "before_update")
def _bloquear_update(mapper: Any, connection: Any, target: AuditLog) -> None:
    """Impede, pelo ORM, a alteração de um registro de auditoria."""
    raise AuditLogImutavelError("Registros de auditoria são imutáveis e não podem ser alterados.")


@event.listens_for(AuditLog, "before_delete")
def _bloquear_delete(mapper: Any, connection: Any, target: AuditLog) -> None:
    """Impede, pelo ORM, a exclusão de um registro de auditoria."""
    raise AuditLogImutavelError("Registros de auditoria são imutáveis e não podem ser apagados.")


_TRIGGERS_SQLITE = (
    """CREATE TRIGGER IF NOT EXISTS audit_logs_bloqueia_update
       BEFORE UPDATE ON audit_logs
       BEGIN SELECT RAISE(ABORT, 'audit_logs e imutavel: UPDATE bloqueado'); END""",
    """CREATE TRIGGER IF NOT EXISTS audit_logs_bloqueia_delete
       BEFORE DELETE ON audit_logs
       BEGIN SELECT RAISE(ABORT, 'audit_logs e imutavel: DELETE bloqueado'); END""",
)


def instalar_protecao_auditoria(sync_connection: Any) -> None:
    """
    Instala no banco os triggers que bloqueiam UPDATE/DELETE em `audit_logs`.
    Idempotente (IF NOT EXISTS), por isso também protege bancos criados antes desta versão.
    Uso: `await conn.run_sync(instalar_protecao_auditoria)` logo após o `create_all`.
    """
    if sync_connection.dialect.name != "sqlite":
        return
    for ddl in _TRIGGERS_SQLITE:
        sync_connection.execute(text(ddl))
