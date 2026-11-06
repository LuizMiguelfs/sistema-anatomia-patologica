"""Provider do módulo de Casos no banco local da aplicação (SQLite).

Executa apenas SQL nativo de ``src/providers/sql/caso/`` e devolve dicionários.
Não contém regra de negócio e NÃO faz commit nas escritas: a transação é controlada
pelo Controller (``commit``/``rollback``), para que caso, movimentação e auditoria
sejam gravados de forma atômica.

Nome e prontuário do paciente são gravados cifrados (AES-256) e decifrados na leitura;
a busca por prontuário usa o índice HMAC (`prontuario_indice`), nunca o valor em claro.
"""
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...helpers.crypto_helper import cifrar, decifrar, indice_busca, normalizar_prontuario
from ...helpers.sql_helper import read_sql_file
from ..interfaces.caso_provider_interface import CasoProviderInterface

_SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")

#: Colunas de `casos` que identificam o paciente e ficam cifradas no banco.
_COLUNAS_CIFRADAS = ("paciente_nome", "prontuario_aghu")


@lru_cache(maxsize=None)
def get_sql_query(file_path: str) -> str:
    """Carrega (e mantém em cache) um template SQL de `src/providers/sql/`."""
    sql_file_path = os.path.join(_SQL_DIR, file_path)
    try:
        return read_sql_file(sql_file_path)
    except FileNotFoundError:
        raise RuntimeError(f"Arquivo SQL não encontrado em: {sql_file_path}")


class CasoSqliteProvider(CasoProviderInterface):
    """Acesso a casos, amostras, movimentações, pendências, fluxo configurável e numeração."""

    def __init__(self, session: AsyncSession) -> None:
        """Recebe a sessão assíncrona do banco local da aplicação."""
        self.session = session

    @staticmethod
    def _decifrar(linha: Dict[str, Any]) -> Dict[str, Any]:
        """Decifra as colunas do paciente presentes na linha."""
        for coluna in _COLUNAS_CIFRADAS:
            if coluna in linha:
                linha[coluna] = decifrar(linha[coluna])
        return linha

    @staticmethod
    def _indice_prontuario(prontuario: Any) -> Optional[str]:
        """Índice de busca do prontuário (só dígitos), ou None."""
        return indice_busca(normalizar_prontuario(str(prontuario))) if prontuario not in (None, "") else None

    async def _all(self, sql_file: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Executa um template e devolve todas as linhas como dicionários (dados do paciente decifrados)."""
        result = await self.session.execute(text(get_sql_query(sql_file)), params)
        return [self._decifrar(dict(row)) for row in result.mappings().all()]

    async def _one(self, sql_file: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Executa um template e devolve a primeira linha, ou None."""
        rows = await self._all(sql_file, params)
        return rows[0] if rows else None

    async def _exec(self, sql_file: str, params: Dict[str, Any]) -> None:
        """Executa um template de escrita (sem commit)."""
        await self.session.execute(text(get_sql_query(sql_file)), params)

    # --- Transação ---------------------------------------------------------
    async def commit(self) -> None:
        """Confirma a transação da sessão."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Desfaz a transação da sessão."""
        await self.session.rollback()

    # --- Casos -------------------------------------------------------------
    async def buscar_por_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Executa `caso/buscar_por_solicitacao.sql`."""
        return await self._one("caso/buscar_por_solicitacao.sql", {"solicitacao_aghu": solicitacao_aghu})

    async def buscar_por_id(self, caso_id: int) -> Optional[Dict[str, Any]]:
        """Executa `caso/buscar_por_id.sql`."""
        return await self._one("caso/buscar_por_id.sql", {"caso_id": caso_id})

    async def proximo_numero(self, sigla: str, ano: int) -> int:
        """Executa `caso/proximo_numero.sql`: reserva o próximo número da sigla no ano (sem commit)."""
        row = await self._one("caso/proximo_numero.sql", {"sigla": sigla, "ano": ano})
        return int(row["ultimo"])

    async def inserir_caso(self, dados: Dict[str, Any]) -> int:
        """Executa `caso/inserir_caso.sql` (nome e prontuário cifrados) e devolve o id do caso."""
        params = {
            **dados,
            "paciente_nome": cifrar(dados["paciente_nome"]),
            "prontuario_aghu": cifrar(dados.get("prontuario_aghu")),
            "prontuario_indice": self._indice_prontuario(dados.get("prontuario_aghu")),
        }
        row = await self._one("caso/inserir_caso.sql", params)
        return int(row["id"])

    async def inserir_amostra(self, caso_id: int, amostra_aghu: str, descricao: Optional[str]) -> None:
        """Executa `caso/inserir_amostra.sql`."""
        await self._exec(
            "caso/inserir_amostra.sql",
            {"caso_id": caso_id, "amostra_aghu": amostra_aghu, "descricao": descricao},
        )

    async def listar_amostras(self, caso_id: int) -> List[Dict[str, Any]]:
        """Executa `caso/listar_amostras.sql`."""
        return await self._all("caso/listar_amostras.sql", {"caso_id": caso_id})

    async def listar_casos(self, filtros: Dict[str, Any], limite: int, deslocamento: int) -> List[Dict[str, Any]]:
        """Executa `caso/listar_casos.sql`."""
        return await self._all(
            "caso/listar_casos.sql",
            {**self._filtros(filtros), "limite": limite, "deslocamento": deslocamento},
        )

    async def contar_casos(self, filtros: Dict[str, Any]) -> int:
        """Executa `caso/contar_casos.sql`."""
        row = await self._one("caso/contar_casos.sql", self._filtros(filtros))
        return int(row["total"]) if row else 0

    @staticmethod
    def _filtros(filtros: Dict[str, Any]) -> Dict[str, Any]:
        """Parâmetros nomeados dos filtros de busca (None = filtro desativado)."""
        return {
            "solicitacao": filtros.get("solicitacao"),
            "prontuario": CasoSqliteProvider._indice_prontuario(filtros.get("prontuario")),
            "identificador": filtros.get("identificador"),
            "tipo_exame": filtros.get("tipo_exame"),
            "etapa": filtros.get("etapa"),
            "status": filtros.get("status"),
        }

    async def atualizar_etapa(self, caso_id: int, etapa_atual: str, status: str, agora: str) -> None:
        """Executa `caso/atualizar_etapa.sql`."""
        await self._exec(
            "caso/atualizar_etapa.sql",
            {"caso_id": caso_id, "etapa_atual": etapa_atual, "status": status, "agora": agora},
        )

    # --- Movimentações (append-only, RNF006) -------------------------------
    async def inserir_movimentacao(self, dados: Dict[str, Any]) -> None:
        """Executa `caso/inserir_movimentacao.sql`."""
        await self._exec("caso/inserir_movimentacao.sql", dados)

    async def listar_movimentacoes(self, caso_id: int) -> List[Dict[str, Any]]:
        """Executa `caso/listar_movimentacoes.sql`."""
        return await self._all("caso/listar_movimentacoes.sql", {"caso_id": caso_id})

    async def ultima_movimentacao_desvio(self, caso_id: int) -> Optional[Dict[str, Any]]:
        """Executa `caso/ultima_movimentacao_desvio.sql`."""
        return await self._one("caso/ultima_movimentacao_desvio.sql", {"caso_id": caso_id})

    # --- Pendências e fluxo configurável (RNF011) --------------------------
    async def contar_pendencias_abertas(self, caso_id: int) -> int:
        """Executa `caso/contar_pendencias_abertas.sql`."""
        row = await self._one("caso/contar_pendencias_abertas.sql", {"caso_id": caso_id})
        return int(row["total"]) if row else 0

    async def destinos(self, tipo_exame: str, etapa_origem: str, tipo: str) -> List[str]:
        """Executa `caso/buscar_transicao.sql`."""
        rows = await self._all(
            "caso/buscar_transicao.sql",
            {"tipo_exame": tipo_exame, "etapa_origem": etapa_origem, "tipo": tipo},
        )
        return [r["etapa_destino"] for r in rows]

    async def etapa_inicial(self, tipo_exame: str) -> Optional[str]:
        """Executa `caso/etapa_inicial.sql`."""
        row = await self._one("caso/etapa_inicial.sql", {"tipo_exame": tipo_exame})
        return row["etapa_destino"] if row else None
