import logging
import os
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...helpers.sql_helper import read_sql_file
from ..interfaces.paciente_provider_interface import PacienteProviderInterface

logger = logging.getLogger("paciente.postgres")

_SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")


@lru_cache(maxsize=None)
def get_sql_query(file_path: str) -> str:
    """Carrega (e mantém em cache) um template SQL de `src/providers/sql/`."""
    sql_file_path = os.path.join(_SQL_DIR, file_path)
    try:
        return read_sql_file(sql_file_path)
    except FileNotFoundError:
        raise RuntimeError(f"Arquivo SQL não encontrado em: {sql_file_path}")


class EscritaAghuDesabilitadaError(PermissionError):
    """Tentativa de escrita no AGHU com PACIENTE_POSTGRES_ESCRITA desabilitada."""


class PacientePostgresProvider(PacienteProviderInterface):
    """
    Provedor de pacientes do AGHU (PostgreSQL, tabela `agh.aip_pacientes`).

    - Leitura: sempre disponível.
    - Escrita (inserir/alterar): só executa com `escrita_habilitada=True`
      (variável PACIENTE_POSTGRES_ESCRITA). O AGHU é somente leitura (RNF005).
    - Exclusão: não suportada, pois a tabela do AGHU não possui coluna de exclusão
      lógica e exclusão física é proibida pelo framework.
    - CPF/CNS: ainda não mapeados para colunas do AGHU (confirmar no dicionário de dados).
    """

    fonte = "POSTGRES"

    def __init__(self, session: AsyncSession, escrita_habilitada: bool = False):
        """Recebe a sessão assíncrona do AGHU e a flag de escrita."""
        self.session = session
        self.escrita_habilitada = escrita_habilitada

    def capacidades(self) -> Dict[str, bool]:
        """Escrita somente com a flag ligada; exclusão nunca."""
        return {"escrita": self.escrita_habilitada, "exclusao": False}

    @staticmethod
    def _normalizar(row: Mapping[str, Any]) -> Dict[str, Any]:
        """Converte uma linha do banco para o formato padrão de paciente da interface."""
        dt_nascimento = row.get("dt_nascimento")
        if isinstance(dt_nascimento, datetime):
            dt_nascimento = dt_nascimento.date()
        elif not isinstance(dt_nascimento, date):
            dt_nascimento = None

        def texto(campo: str) -> Optional[str]:
            """Texto do campo sem espaços nas pontas; vazio vira None."""
            valor = row.get(campo)
            if valor is None:
                return None
            valor = str(valor).strip()
            return valor or None

        return {
            "codigo": int(row["codigo"]),
            "nome": texto("nome") or "",
            "dt_nascimento": dt_nascimento,
            "sexo": texto("sexo"),
            "cor": texto("cor"),
            "nome_mae": texto("nome_mae"),
            "nome_pai": texto("nome_pai"),
            "cpf": None,
            "cns": None,
        }

    async def _executar(self, arquivo_sql: str, params: Dict[str, Any], escrita: bool = False) -> List[Dict[str, Any]]:
        """Executa um template SQL, convertendo falhas de banco em HTTP 503 (sem vazar detalhes)."""
        query = text(get_sql_query(arquivo_sql))
        try:
            result = await self.session.execute(query, params)
            rows = [dict(r) for r in result.mappings().all()]
            if escrita:
                await self.session.commit()
            return rows
        except (SQLAlchemyError, OSError) as exc:
            # OSError cobre falhas de rede/timeout na conexão, que o asyncpg não encapsula.
            if escrita:
                try:
                    await self.session.rollback()
                except (SQLAlchemyError, OSError):
                    pass
            logger.error("Falha ao executar %s no AGHU: %s", arquivo_sql, exc.__class__.__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falha de comunicação com o banco do AGHU. Tente novamente em instantes.",
            )

    def _garantir_escrita(self) -> None:
        """Bloqueia qualquer escrita quando a flag não estiver habilitada (defesa em profundidade)."""
        if not self.escrita_habilitada:
            raise EscritaAghuDesabilitadaError("Escrita no AGHU desabilitada (PACIENTE_POSTGRES_ESCRITA=false).")

    async def listar_pacientes(
        self, termo: Optional[str] = None, limite: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Lista pacientes do AGHU filtrando por nome (ILIKE) ou código."""
        termo = (termo or "").strip() or None
        params = {
            "termo": termo,
            "padrao": f"%{termo}%" if termo else None,
            "limite": limite,
            "offset": offset,
        }
        rows = await self._executar("paciente/listar_pacientes.sql", params)
        return [self._normalizar(r) for r in rows]

    async def obter_paciente_por_codigo(self, codigo: int) -> Optional[Dict[str, Any]]:
        """Busca um paciente do AGHU pelo código."""
        rows = await self._executar("paciente/obter_paciente.sql", {"codigo": codigo})
        return self._normalizar(rows[0]) if rows else None

    async def existe_cpf(self, cpf: str, ignorar_codigo: Optional[int] = None) -> bool:
        """CPF ainda não mapeado no AGHU: a checagem de duplicidade não se aplica a esta fonte."""
        return False

    @staticmethod
    def _params_escrita(dados: Dict[str, Any]) -> Dict[str, Any]:
        """Seleciona apenas as colunas mapeadas no AGHU."""
        return {
            "nome": dados.get("nome"),
            "dt_nascimento": dados.get("dt_nascimento"),
            "sexo": dados.get("sexo"),
            "cor": dados.get("cor"),
            "nome_mae": dados.get("nome_mae"),
            "nome_pai": dados.get("nome_pai"),
        }

    async def criar_paciente(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Insere um paciente (somente com a flag de escrita habilitada)."""
        self._garantir_escrita()
        rows = await self._executar("paciente/inserir_paciente.sql", self._params_escrita(dados), escrita=True)
        return self._normalizar(rows[0])

    async def atualizar_paciente(self, codigo: int, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualiza um paciente (somente com a flag de escrita habilitada)."""
        self._garantir_escrita()
        params = {**self._params_escrita(dados), "codigo": codigo}
        rows = await self._executar("paciente/atualizar_paciente.sql", params, escrita=True)
        return self._normalizar(rows[0]) if rows else None

    async def excluir_paciente(self, codigo: int) -> Optional[Dict[str, Any]]:
        """Não suportado no AGHU (sem coluna de exclusão lógica; exclusão física é proibida)."""
        raise EscritaAghuDesabilitadaError("Exclusão de pacientes não é suportada na fonte AGHU.")
