"""Provider SOMENTE LEITURA do AGHU para solicitações de exame (RF003, RNF005).

Nenhum comando de escrita é emitido contra o AGHU: apenas os SELECT de
``src/providers/sql/aghu/``.
"""
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...helpers.sql_helper import read_sql_file
from ..interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface

_SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")


@lru_cache(maxsize=None)
def get_sql_query(file_path: str) -> str:
    """Carrega (e mantém em cache) um template SQL de `src/providers/sql/`."""
    sql_file_path = os.path.join(_SQL_DIR, file_path)
    try:
        return read_sql_file(sql_file_path)
    except FileNotFoundError:
        raise RuntimeError(f"Arquivo SQL não encontrado em: {sql_file_path}")


class AghuSolicitacaoPostgresProvider(AghuSolicitacaoProviderInterface):
    """Consulta paciente, solicitação e amostras no AGHU Slave (PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        """Recebe a sessão somente leitura do AGHU."""
        self.session = session

    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Executa `aghu/buscar_solicitacao.sql`."""
        result = await self.session.execute(
            text(get_sql_query("aghu/buscar_solicitacao.sql")),
            {"solicitacao_aghu": int(solicitacao_aghu)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        """Executa `aghu/listar_amostras_solicitacao.sql`."""
        result = await self.session.execute(
            text(get_sql_query("aghu/listar_amostras_solicitacao.sql")),
            {"solicitacao_aghu": int(solicitacao_aghu)},
        )
        return [dict(row) for row in result.mappings().all()]
