"""Provider do módulo de Casos (banco local da aplicação).

Executa apenas SQL nativo de ``src/providers/sql/caso/`` e devolve dicionários.
Não contém regra de negócio e NÃO faz commit: a transação é controlada pelo
Controller (``commit``/``rollback``), para que caso, movimentação e auditoria
sejam gravados de forma atômica.
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


class CasoPostgresProvider:
    """Acesso a dados de casos, amostras, movimentações e fluxo configurável."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _all(self, sql_file: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = await self.session.execute(text(get_sql_query(sql_file)), params)
        return [dict(row) for row in result.mappings().all()]

    async def _one(self, sql_file: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rows = await self._all(sql_file, params)
        return rows[0] if rows else None

    async def _exec(self, sql_file: str, params: Dict[str, Any]) -> None:
        await self.session.execute(text(get_sql_query(sql_file)), params)

    # --- Transação ---------------------------------------------------------
    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    # --- Casos -------------------------------------------------------------
    async def buscar_por_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        return await self._one("caso/buscar_por_solicitacao.sql", {"solicitacao_aghu": solicitacao_aghu})

    async def buscar_por_id(self, caso_id: int) -> Optional[Dict[str, Any]]:
        return await self._one("caso/buscar_por_id.sql", {"caso_id": caso_id})

    async def inserir_caso(self, dados: Dict[str, Any]) -> int:
        row = await self._one("caso/inserir_caso.sql", dados)
        return int(row["id"])

    async def definir_identificador(self, caso_id: int, identificador_interno: str) -> None:
        await self._exec(
            "caso/definir_identificador.sql",
            {"caso_id": caso_id, "identificador_interno": identificador_interno},
        )

    async def inserir_amostra(self, caso_id: int, amostra_aghu: str, descricao: Optional[str]) -> None:
        await self._exec(
            "caso/inserir_amostra.sql",
            {"caso_id": caso_id, "amostra_aghu": amostra_aghu, "descricao": descricao},
        )

    async def listar_amostras(self, caso_id: int) -> List[Dict[str, Any]]:
        return await self._all("caso/listar_amostras.sql", {"caso_id": caso_id})

    async def listar_casos(self, filtros: Dict[str, Any], limite: int, deslocamento: int) -> List[Dict[str, Any]]:
        return await self._all(
            "caso/listar_casos.sql",
            {**self._filtros(filtros), "limite": limite, "deslocamento": deslocamento},
        )

    async def contar_casos(self, filtros: Dict[str, Any]) -> int:
        row = await self._one("caso/contar_casos.sql", self._filtros(filtros))
        return int(row["total"]) if row else 0

    @staticmethod
    def _filtros(filtros: Dict[str, Any]) -> Dict[str, Any]:
        paciente = filtros.get("paciente")
        return {
            "solicitacao": filtros.get("solicitacao"),
            "paciente": f"%{paciente.lower()}%" if paciente else None,
            "identificador": filtros.get("identificador"),
            "tipo_exame": filtros.get("tipo_exame"),
            "etapa": filtros.get("etapa"),
            "status": filtros.get("status"),
        }

    async def atualizar_etapa(self, caso_id: int, etapa_atual: str, status: str, agora: str) -> None:
        await self._exec(
            "caso/atualizar_etapa.sql",
            {"caso_id": caso_id, "etapa_atual": etapa_atual, "status": status, "agora": agora},
        )

    # --- Movimentações (append-only, RNF006) -------------------------------
    async def inserir_movimentacao(self, dados: Dict[str, Any]) -> None:
        await self._exec("caso/inserir_movimentacao.sql", dados)

    async def listar_movimentacoes(self, caso_id: int) -> List[Dict[str, Any]]:
        return await self._all("caso/listar_movimentacoes.sql", {"caso_id": caso_id})

    async def ultima_movimentacao_desvio(self, caso_id: int) -> Optional[Dict[str, Any]]:
        return await self._one("caso/ultima_movimentacao_desvio.sql", {"caso_id": caso_id})

    # --- Pendências e fluxo configurável (RNF011) --------------------------
    async def contar_pendencias_abertas(self, caso_id: int) -> int:
        row = await self._one("caso/contar_pendencias_abertas.sql", {"caso_id": caso_id})
        return int(row["total"]) if row else 0

    async def destinos(self, tipo_exame: str, etapa_origem: str, tipo: str) -> List[str]:
        rows = await self._all(
            "caso/buscar_transicao.sql",
            {"tipo_exame": tipo_exame, "etapa_origem": etapa_origem, "tipo": tipo},
        )
        return [r["etapa_destino"] for r in rows]

    async def etapa_inicial(self, tipo_exame: str) -> Optional[str]:
        row = await self._one("caso/etapa_inicial.sql", {"tipo_exame": tipo_exame})
        return row["etapa_destino"] if row else None