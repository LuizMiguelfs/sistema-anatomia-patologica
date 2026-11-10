from typing import Callable
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .providers.interfaces.paciente_provider_interface import PacienteProviderInterface
from .providers.implementations.paciente_postgres_provider import PacientePostgresProvider
from .providers.implementations.paciente_csv_provider import PacienteCsvProvider
from .resources.database import get_aghu_db_session

# 1. Funções "getter" simples e independentes (privadas por convenção)
def _get_paciente_postgres_provider(
    session: AsyncSession = Depends(get_aghu_db_session)
) -> PacienteProviderInterface:
    """Provedor AGHU (Postgres). Escrita só com PACIENTE_POSTGRES_ESCRITA=true (RNF005)."""
    return PacientePostgresProvider(session=session, escrita_habilitada=False)

def _get_paciente_csv_provider() -> PacienteProviderInterface:
    """Provedor CSV para desenvolvimento offline (caminho em PACIENTE_CSV_PATH)."""
    return PacienteCsvProvider(csv_path=settings.PACIENTE_CSV_PATH)

# 2. A FÁBRICA: A única função que o roteador vai conhecer.
def get_paciente_provider(strategy: str) -> Callable[..., PacienteProviderInterface]:
    """
    Esta é uma fábrica. Baseado na string 'strategy', ela não retorna o provedor,
    mas sim a FUNÇÃO DE DEPENDÊNCIA correta que o FastAPI deve usar.
    """
    if strategy.upper() == "POSTGRES":
        return _get_paciente_postgres_provider
    elif strategy.upper() == "CSV":
        return _get_paciente_csv_provider
    else:
        raise ValueError(f"Estratégia de provedor desconhecida: {strategy}")


# 3. Auditoria: leitura da trilha `audit_logs` no banco local da aplicação (app.db).
from .providers.interfaces.auditoria_provider_interface import AuditoriaProviderInterface
from .providers.implementations.auditoria_sqlite_provider import AuditoriaSqliteProvider
from .resources.database import get_app_db_session


def get_auditoria_provider(
    session: AsyncSession = Depends(get_app_db_session)
) -> AuditoriaProviderInterface:
    """Provedor de leitura da trilha de auditoria (banco local da aplicação)."""
    return AuditoriaSqliteProvider(session=session)


# 4. Gestão de usuários: usuários autorizados (`authorized_users`) no banco local da aplicação.
from .providers.interfaces.usuario_provider_interface import UsuarioProviderInterface
from .providers.implementations.usuario_sqlite_provider import UsuarioSqliteProvider


def get_usuario_provider(
    session: AsyncSession = Depends(get_app_db_session)
) -> UsuarioProviderInterface:
    """Provedor dos usuários autorizados (banco local da aplicação)."""
    return UsuarioSqliteProvider(session=session)


# 5. Painel de indicadores: banco local (dados reais, sem inferência de eventos não capturados).
from .providers.interfaces.dashboard_provider_interface import DashboardProviderInterface
from .providers.implementations.dashboard_sqlite_provider import DashboardSqliteProvider


def get_dashboard_provider(
    session: AsyncSession = Depends(get_app_db_session),
) -> DashboardProviderInterface:
    """Consulta indicadores reais; prazos só se parametrizados e homologados."""
    return DashboardSqliteProvider(session, prazos=settings.prazos_exame_horas())


# 6. Casos (Membro 4): casos no banco local e leitura de solicitações no AGHU.
from .providers.interfaces.caso_provider_interface import CasoProviderInterface
from .providers.implementations.caso_sqlite_provider import CasoSqliteProvider
from .providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface
from .providers.implementations.aghu_solicitacao_postgres_provider import AghuSolicitacaoPostgresProvider


def get_caso_provider(
    session: AsyncSession = Depends(get_app_db_session),
) -> CasoProviderInterface:
    """Provedor dos casos (banco local da aplicação)."""
    return CasoSqliteProvider(session=session)


def get_aghu_solicitacao_provider(
    session: AsyncSession = Depends(get_aghu_db_session),
) -> AghuSolicitacaoProviderInterface:
    """Provedor somente leitura das solicitações de exame no AGHU (RNF005)."""
    return AghuSolicitacaoPostgresProvider(session=session)
