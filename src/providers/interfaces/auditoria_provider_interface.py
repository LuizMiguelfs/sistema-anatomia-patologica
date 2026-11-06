from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class AuditoriaProviderInterface(ABC):
    """
    Interface (contrato) para provedores de leitura da trilha de auditoria (`audit_logs`).

    Somente leitura: a trilha é imutável e a gravação é feita por `helpers/audit_helper`.

    Formato padrão de um registro retornado (dicionário):
        id (int), created_at (datetime, UTC com fuso), usuario, categoria, acao, recurso (str),
        dados_anteriores, dados_novos (str JSON | None), ip_origem (str | None, ausente no histórico).

    Provedores NÃO aplicam regras de negócio (validação de período, fuso, prefixo, quem pode ver):
    isso é responsabilidade do controller. Filtros com valor None são ignorados.
    """

    @abstractmethod
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
        """
        Lista registros mais recentes primeiro. `recurso_prefixo` é um prefixo literal
        (sem curingas). `inicio`/`fim` são instantes UTC do intervalo [inicio, fim).
        """

    @abstractmethod
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
        """Conta os registros com os mesmos filtros de `listar_logs`."""

    @abstractmethod
    async def listar_historico(
        self, recurso: str, categoria: str, limite: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Linha do tempo de um recurso exato em uma categoria, mais recentes primeiro, sem IP."""

    @abstractmethod
    async def contar_historico(self, recurso: str, categoria: str) -> int:
        """Conta os registros do histórico de um recurso em uma categoria."""
