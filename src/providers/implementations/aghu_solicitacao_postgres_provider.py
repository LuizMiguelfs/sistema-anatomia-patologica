"""Provider SOMENTE LEITURA do AGHU para solicitações de exame (RF003, RNF005).

Nenhum comando de escrita é emitido contra o AGHU: apenas os SELECT de
``src/providers/sql/aghu/``.
"""
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def get_sql_query(file_path: str) -> str:
    """Carrega um arquivo SQL de ``src/providers/sql/``."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file_path = os.path.join(base_dir, "..", "sql", file_path)
    with open(sql_file_path, "r", encoding="utf-8") as f:
        return f.read()


class AghuSolicitacaoPostgresProvider:
    """Consulta paciente, solicitação e amostras no AGHU Slave."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            text(get_sql_query("aghu/buscar_solicitacao.sql")),
            {"solicitacao_aghu": int(solicitacao_aghu)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            text(get_sql_query("aghu/listar_amostras_solicitacao.sql")),
            {"solicitacao_aghu": int(solicitacao_aghu)},
        )
        return [dict(row) for row in result.mappings().all()]