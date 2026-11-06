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
    return PacientePostgresProvider(session=session, escrita_habilitada=settings.PACIENTE_POSTGRES_ESCRITA)

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
