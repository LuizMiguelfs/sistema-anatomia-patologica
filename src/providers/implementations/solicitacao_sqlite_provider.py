"""Provider do módulo de Solicitações no banco local da aplicação (SQLite).

Executa apenas SQL nativo de ``src/providers/sql/solicitacao/`` e devolve dicionários.
Não contém regra de negócio e NÃO faz commit nas escritas: a transação é controlada
pelo Controller (``commit``/``rollback``), para que solicitação, movimentação e auditoria
sejam gravados de forma atômica.

Nome e prontuário do paciente são gravados cifrados (AES-256) e decifrados na leitura;
a busca por prontuário usa o índice HMAC (`prontuario_indice`), nunca o valor em claro.
"""
import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...helpers.crypto_helper import cifrar, decifrar, indice_busca, normalizar_prontuario
from ...helpers.sql_helper import read_sql_file
from ..interfaces.solicitacao_provider_interface import SolicitacaoProviderInterface

_SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")

#: Colunas de `solicitacoes_exame` que identificam o paciente e ficam cifradas no banco.
_COLUNAS_CIFRADAS = ("paciente_nome", "prontuario_aghu")


@lru_cache(maxsize=None)
def get_sql_query(file_path: str) -> str:
    """Carrega (e mantém em cache) um template SQL de `src/providers/sql/`."""
    sql_file_path = os.path.join(_SQL_DIR, file_path)
    try:
        return read_sql_file(sql_file_path)
    except FileNotFoundError:
        raise RuntimeError(f"Arquivo SQL não encontrado em: {sql_file_path}")


class SolicitacaoSqliteProvider(SolicitacaoProviderInterface):
    """Acesso a solicitações, amostras, movimentações, pendências, fluxo configurável e numeração."""

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

    # --- Solicitações -------------------------------------------------------------
    async def buscar_por_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Executa `solicitacao/buscar_por_solicitacao.sql`."""
        return await self._one("solicitacao/buscar_por_solicitacao.sql", {"solicitacao_aghu": solicitacao_aghu})

    async def buscar_por_id(self, solicitacao_id: int) -> Optional[Dict[str, Any]]:
        """Executa `solicitacao/buscar_por_id.sql`."""
        return await self._one("solicitacao/buscar_por_id.sql", {"solicitacao_id": solicitacao_id})

    async def proximo_numero(self, sigla: str, ano: int) -> int:
        """Executa `solicitacao/proximo_numero.sql`: reserva o próximo número da sigla no ano (sem commit)."""
        row = await self._one("solicitacao/proximo_numero.sql", {"sigla": sigla, "ano": ano})
        return int(row["ultimo"])

    async def inserir_solicitacao(self, dados: Dict[str, Any]) -> int:
        """Executa `solicitacao/inserir_solicitacao.sql` (nome e prontuário cifrados) e devolve o id da solicitação."""
        params = {
            **dados,
            "paciente_nome": cifrar(dados["paciente_nome"]),
            "prontuario_aghu": cifrar(dados.get("prontuario_aghu")),
            "prontuario_indice": self._indice_prontuario(dados.get("prontuario_aghu")),
        }
        row = await self._one("solicitacao/inserir_solicitacao.sql", params)
        return int(row["id"])

    async def atualizar_dados_aghu(self, solicitacao_id: int, nome: str, prontuario: Optional[str], agora: str) -> None:
        """Atualiza o snapshot cifrado de nome/prontuário, nunca o AGHU."""
        await self._exec("solicitacao/atualizar_dados_aghu.sql", {
            "solicitacao_id": solicitacao_id,
            "paciente_nome": cifrar(nome),
            "prontuario_aghu": cifrar(prontuario),
            "prontuario_indice": self._indice_prontuario(prontuario),
            "agora": agora,
        })

    async def inserir_amostra(self, solicitacao_id: int, amostra_aghu: str, descricao: Optional[str]) -> None:
        """Executa `solicitacao/inserir_amostra.sql`."""
        await self._exec(
            "solicitacao/inserir_amostra.sql",
            {"solicitacao_id": solicitacao_id, "amostra_aghu": amostra_aghu, "descricao": descricao},
        )

    async def listar_amostras(self, solicitacao_id: int) -> List[Dict[str, Any]]:
        """Executa `solicitacao/listar_amostras.sql`."""
        return await self._all("solicitacao/listar_amostras.sql", {"solicitacao_id": solicitacao_id})

    async def buscar_solicitacoes(self, filtros: Dict[str, Any], limite: int, deslocamento: int) -> List[Dict[str, Any]]:
        """Executa `solicitacao/buscar_solicitacoes.sql`."""
        return await self._all(
            "solicitacao/buscar_solicitacoes.sql",
            {**self._filtros(filtros), "limite": limite, "deslocamento": deslocamento},
        )

    async def contar_busca_solicitacoes(self, filtros: Dict[str, Any]) -> int:
        """Executa `solicitacao/contar_busca_solicitacoes.sql`."""
        row = await self._one("solicitacao/contar_busca_solicitacoes.sql", self._filtros(filtros))
        return int(row["total"]) if row else 0

    @staticmethod
    def _filtros(filtros: Dict[str, Any]) -> Dict[str, Any]:
        """Parâmetros nomeados dos filtros de busca (None = filtro desativado)."""
        return {
            "solicitacao": filtros.get("solicitacao"),
            "prontuario": SolicitacaoSqliteProvider._indice_prontuario(filtros.get("prontuario")),
            "identificador": filtros.get("identificador"),
            "tipo_exame": filtros.get("tipo_exame"),
            "etapa": filtros.get("etapa"),
            "status": filtros.get("status"),
        }

    async def atualizar_etapa(self, solicitacao_id: int, etapa_atual: str, status: str, agora: str) -> None:
        """Executa `solicitacao/atualizar_etapa.sql`."""
        await self._exec(
            "solicitacao/atualizar_etapa.sql",
            {"solicitacao_id": solicitacao_id, "etapa_atual": etapa_atual, "status": status, "agora": agora},
        )

    # --- Movimentações (append-only, RNF006) -------------------------------
    async def inserir_movimentacao(self, dados: Dict[str, Any]) -> None:
        """Executa `solicitacao/inserir_movimentacao.sql`."""
        await self._exec("solicitacao/inserir_movimentacao.sql", dados)

    async def listar_movimentacoes(self, solicitacao_id: int) -> List[Dict[str, Any]]:
        """Executa `solicitacao/listar_movimentacoes.sql`."""
        return await self._all("solicitacao/listar_movimentacoes.sql", {"solicitacao_id": solicitacao_id})

    async def ultima_movimentacao_desvio(self, solicitacao_id: int) -> Optional[Dict[str, Any]]:
        """Executa `solicitacao/ultima_movimentacao_desvio.sql`."""
        return await self._one("solicitacao/ultima_movimentacao_desvio.sql", {"solicitacao_id": solicitacao_id})

    # --- Pendências e fluxo configurável (RNF011) --------------------------
    async def contar_pendencias_abertas(self, solicitacao_id: int) -> int:
        """Executa `solicitacao/contar_pendencias_abertas.sql`."""
        row = await self._one("solicitacao/contar_pendencias_abertas.sql", {"solicitacao_id": solicitacao_id})
        return int(row["total"]) if row else 0

    async def destinos(self, tipo_exame: str, etapa_origem: str, tipo: str) -> List[str]:
        """Executa `solicitacao/buscar_transicao.sql`."""
        rows = await self._all(
            "solicitacao/buscar_transicao.sql",
            {"tipo_exame": tipo_exame, "etapa_origem": etapa_origem, "tipo": tipo},
        )
        return [r["etapa_destino"] for r in rows]

    async def etapa_inicial(self, tipo_exame: str) -> Optional[str]:
        """Executa `solicitacao/etapa_inicial.sql`."""
        row = await self._one("solicitacao/etapa_inicial.sql", {"tipo_exame": tipo_exame})
        return row["etapa_destino"] if row else None

    # --- MVP: Solicitações de Exames, retirada e formulários por fase ---------
    @staticmethod
    def _filtros_busca(filtros: Dict[str, Any]) -> Dict[str, Any]:
        """Parâmetros da busca única por código AGHU, código interno ou prontuário (índice HMAC)."""
        busca = filtros.get("busca")
        return {
            "tipo_exame": filtros.get("tipo_exame"),
            "busca": busca,
            "busca_identificador": busca.upper() if busca else None,
            "busca_prontuario": SolicitacaoSqliteProvider._indice_prontuario(busca) if busca else None,
        }

    def _filtros_solicitacoes(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """Parâmetros de `solicitacao/listar_solicitacoes.sql` e `solicitacao/contar_solicitacoes.sql`."""
        return {
            **self._filtros_busca(filtros),
            "situacao": filtros["situacao"], "de": filtros.get("de"), "ate": filtros.get("ate"),
        }

    async def listar_solicitacoes(self, filtros: Dict[str, Any], limite: int, deslocamento: int) -> List[Dict[str, Any]]:
        """Executa `solicitacao/listar_solicitacoes.sql`."""
        return await self._all(
            "solicitacao/listar_solicitacoes.sql",
            {**self._filtros_solicitacoes(filtros), "limite": limite, "deslocamento": deslocamento},
        )

    async def contar_solicitacoes(self, filtros: Dict[str, Any]) -> int:
        """Executa `solicitacao/contar_solicitacoes.sql`."""
        row = await self._one("solicitacao/contar_solicitacoes.sql", self._filtros_solicitacoes(filtros))
        return int(row["total"]) if row else 0

    async def listar_fila(
        self, etapa: str, filtros: Dict[str, Any], concluidas_desde: str, limite: int, deslocamento: int
    ) -> List[Dict[str, Any]]:
        """Executa `solicitacao/listar_fila_fase.sql`."""
        return await self._all("solicitacao/listar_fila_fase.sql", {
            **self._filtros_busca(filtros), "etapa": etapa, "concluidas_desde": concluidas_desde,
            "limite": limite, "deslocamento": deslocamento,
        })

    async def contar_fila(self, etapa: str, filtros: Dict[str, Any], concluidas_desde: str) -> int:
        """Executa `solicitacao/contar_fila_fase.sql`."""
        row = await self._one("solicitacao/contar_fila_fase.sql", {
            **self._filtros_busca(filtros), "etapa": etapa, "concluidas_desde": concluidas_desde,
        })
        return int(row["total"]) if row else 0

    async def marcar_retirada(self, solicitacao_id: int, etapa_atual: str, status: str, usuario: str, agora: str) -> None:
        """Executa `solicitacao/marcar_retirada.sql`."""
        await self._exec("solicitacao/marcar_retirada.sql", {
            "solicitacao_id": solicitacao_id, "etapa_atual": etapa_atual, "status": status, "usuario": usuario, "agora": agora,
        })

    async def desfazer_retirada(self, solicitacao_id: int, status: str, agora: str) -> None:
        """Executa `solicitacao/desfazer_retirada.sql`."""
        await self._exec("solicitacao/desfazer_retirada.sql", {"solicitacao_id": solicitacao_id, "status": status, "agora": agora})

    async def buscar_fase(self, solicitacao_id: int, etapa: str) -> Optional[Dict[str, Any]]:
        """Executa `solicitacao/buscar_fase.sql` e decodifica o JSON do formulário."""
        row = await self._one("solicitacao/buscar_fase.sql", {"solicitacao_id": solicitacao_id, "etapa": etapa})
        if row:
            row["dados"] = json.loads(row["dados"] or "{}")
        return row

    async def salvar_fase(self, dados: Dict[str, Any]) -> None:
        """Executa `solicitacao/salvar_fase.sql` (formulário gravado como JSON)."""
        await self._exec("solicitacao/salvar_fase.sql", {
            "solicitacao_id": dados["solicitacao_id"], "etapa": dados["etapa"],
            "dados": json.dumps(dados["dados"], ensure_ascii=False),
            "situacao": dados["situacao"], "usuario": dados["usuario"], "agora": dados["agora"],
            "concluido_por": dados.get("concluido_por"), "concluido_em": dados.get("concluido_em"),
        })
