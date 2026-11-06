import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...helpers.sql_helper import read_sql_file
from ..interfaces.auditoria_provider_interface import AuditoriaProviderInterface

_SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")

#: Formato em que o SQLAlchemy grava DateTime no SQLite (comparação textual correta).
_FORMATO_DATA_SQLITE = "%Y-%m-%d %H:%M:%S.%f"


@lru_cache(maxsize=None)
def get_sql_query(file_path: str) -> str:
    """Carrega (e mantém em cache) um template SQL de `src/providers/sql/`."""
    sql_file_path = os.path.join(_SQL_DIR, file_path)
    try:
        return read_sql_file(sql_file_path)
    except FileNotFoundError:
        raise RuntimeError(f"Arquivo SQL não encontrado em: {sql_file_path}")


def _escapar_like(valor: str) -> str:
    """Escapa os curingas do LIKE (`\\`, `%`, `_`) para buscar o texto literalmente."""
    return valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _data_sqlite(momento: Optional[datetime]) -> Optional[str]:
    """Converte um instante para o texto UTC no formato gravado no SQLite."""
    if momento is None:
        return None
    if momento.tzinfo is not None:
        momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
    return momento.strftime(_FORMATO_DATA_SQLITE)


def _ler_data(valor: Any) -> datetime:
    """Lê a data do banco (texto ou datetime) e devolve com fuso UTC explícito."""
    momento = valor if isinstance(valor, datetime) else datetime.fromisoformat(str(valor))
    return momento.replace(tzinfo=timezone.utc) if momento.tzinfo is None else momento


class AuditoriaSqliteProvider(AuditoriaProviderInterface):
    """
    Provedor de leitura da trilha de auditoria no banco local da aplicação (`data/app.db`).
    Executa os templates de `src/providers/sql/auditoria/`.
    """

    def __init__(self, session: AsyncSession):
        """Recebe a sessão assíncrona do banco local da aplicação."""
        self.session = session

    @staticmethod
    def _normalizar(row: Mapping[str, Any]) -> Dict[str, Any]:
        """Converte uma linha do banco para o formato padrão da interface."""
        registro = dict(row)
        registro["created_at"] = _ler_data(registro["created_at"])
        return registro

    @staticmethod
    def _filtros(
        usuario: Optional[str],
        categoria: Optional[str],
        acao: Optional[str],
        recurso: Optional[str],
        recurso_prefixo: Optional[str],
        inicio: Optional[datetime],
        fim: Optional[datetime],
    ) -> Dict[str, Any]:
        """Monta os parâmetros nomeados dos templates (None = filtro desativado)."""
        return {
            "usuario": usuario,
            "categoria": categoria,
            "acao": acao,
            "recurso": recurso,
            "recurso_prefixo": None if recurso_prefixo is None else _escapar_like(recurso_prefixo) + "%",
            "inicio": _data_sqlite(inicio),
            "fim": _data_sqlite(fim),
        }

    async def listar_logs(
        self,
        usuario: Optional[str] = None,
        categoria: Optional[str] = None,
        acao: Optional[str] = None,
        recurso: Optional[str] = None,
        recurso_prefixo: Optional[str] = None,
        inicio: Optional[datetime] = None,
        fim: Optional[datetime] = None,
        limite: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Executa `auditoria/listar_logs.sql`."""
        params = self._filtros(usuario, categoria, acao, recurso, recurso_prefixo, inicio, fim)
        result = await self.session.execute(
            text(get_sql_query("auditoria/listar_logs.sql")), {**params, "limite": limite, "offset": offset}
        )
        return [self._normalizar(row) for row in result.mappings().all()]

    async def contar_logs(
        self,
        usuario: Optional[str] = None,
        categoria: Optional[str] = None,
        acao: Optional[str] = None,
        recurso: Optional[str] = None,
        recurso_prefixo: Optional[str] = None,
        inicio: Optional[datetime] = None,
        fim: Optional[datetime] = None,
    ) -> int:
        """Executa `auditoria/contar_logs.sql`."""
        params = self._filtros(usuario, categoria, acao, recurso, recurso_prefixo, inicio, fim)
        result = await self.session.execute(text(get_sql_query("auditoria/contar_logs.sql")), params)
        return int(result.scalar_one())

    async def listar_historico(
        self, recurso: str, categoria: str, limite: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Executa `auditoria/listar_historico.sql`."""
        result = await self.session.execute(
            text(get_sql_query("auditoria/listar_historico.sql")),
            {"recurso": recurso, "categoria": categoria, "limite": limite, "offset": offset},
        )
        return [self._normalizar(row) for row in result.mappings().all()]

    async def contar_historico(self, recurso: str, categoria: str) -> int:
        """Executa `auditoria/contar_historico.sql`."""
        result = await self.session.execute(
            text(get_sql_query("auditoria/contar_historico.sql")), {"recurso": recurso, "categoria": categoria}
        )
        return int(result.scalar_one())
