import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...helpers.sql_helper import read_sql_file
from ..interfaces.usuario_provider_interface import UsuarioProviderInterface

_SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")

#: Formato em que o SQLAlchemy grava DateTime no SQLite.
_FORMATO_DATA_SQLITE = "%Y-%m-%d %H:%M:%S.%f"


@lru_cache(maxsize=None)
def get_sql_query(file_path: str) -> str:
    """Carrega (e mantém em cache) um template SQL de `src/providers/sql/`."""
    sql_file_path = os.path.join(_SQL_DIR, file_path)
    try:
        return read_sql_file(sql_file_path)
    except FileNotFoundError:
        raise RuntimeError(f"Arquivo SQL não encontrado em: {sql_file_path}")


def _data_sqlite(momento: datetime) -> str:
    """Converte um instante para o texto UTC no formato gravado no SQLite."""
    if momento.tzinfo is not None:
        momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
    return momento.strftime(_FORMATO_DATA_SQLITE)


def _ler_data(valor: Any) -> Optional[datetime]:
    """Lê a data do banco (texto ou datetime) e devolve com fuso UTC explícito."""
    if valor is None:
        return None
    momento = valor if isinstance(valor, datetime) else datetime.fromisoformat(str(valor))
    return momento.replace(tzinfo=timezone.utc) if momento.tzinfo is None else momento.astimezone(timezone.utc)


class UsuarioSqliteProvider(UsuarioProviderInterface):
    """
    Provedor dos usuários autorizados no banco local da aplicação (`data/app.db`).
    Executa os templates de `src/providers/sql/usuarios/`.
    """

    def __init__(self, session: AsyncSession):
        """Recebe a sessão assíncrona do banco local da aplicação."""
        self.session = session

    @staticmethod
    def _normalizar(row: Mapping[str, Any]) -> Dict[str, Any]:
        """Converte uma linha do banco para o formato padrão da interface."""
        return {
            "username": row["username"],
            "nome": row["nome"],
            "perfil": row["role"],
            "ativo": bool(row["active"]),
            "criado_em": _ler_data(row["created_at"]),
            "atualizado_em": _ler_data(row["updated_at"]),
        }

    async def listar(self) -> List[Dict[str, Any]]:
        """Executa `usuarios/listar_usuarios.sql`."""
        result = await self.session.execute(text(get_sql_query("usuarios/listar_usuarios.sql")))
        return [self._normalizar(row) for row in result.mappings().all()]

    async def buscar(self, username: str) -> Optional[Dict[str, Any]]:
        """Executa `usuarios/buscar_usuario.sql`."""
        result = await self.session.execute(
            text(get_sql_query("usuarios/buscar_usuario.sql")), {"username": username}
        )
        row = result.mappings().first()
        return self._normalizar(row) if row else None

    async def inserir(self, username: str, nome: Optional[str], perfil: str, agora: datetime) -> None:
        """Executa `usuarios/inserir_usuario.sql` (sem commit)."""
        await self.session.execute(
            text(get_sql_query("usuarios/inserir_usuario.sql")),
            {"username": username, "nome": nome, "role": perfil, "agora": _data_sqlite(agora)},
        )

    async def atualizar(self, username: str, perfil: str, ativo: bool, agora: datetime) -> None:
        """Executa `usuarios/atualizar_usuario.sql` (sem commit)."""
        await self.session.execute(
            text(get_sql_query("usuarios/atualizar_usuario.sql")),
            {"username": username, "role": perfil, "active": 1 if ativo else 0, "agora": _data_sqlite(agora)},
        )

    async def commit(self) -> None:
        """Confirma a transação da sessão."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Desfaz a transação da sessão."""
        await self.session.rollback()
