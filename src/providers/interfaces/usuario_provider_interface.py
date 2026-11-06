from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class UsuarioProviderInterface(ABC):
    """
    Interface (contrato) para provedores dos usuários autorizados no SAP (`authorized_users`).

    Formato padrão de um usuário retornado (dicionário):
        username (str), nome (str | None), perfil (str), ativo (bool),
        criado_em (datetime UTC), atualizado_em (datetime UTC | None).

    Provedores NÃO aplicam regras de negócio (quem pode alterar, auto-alteração, AD):
    isso é responsabilidade do controller. Não existe exclusão de usuário.

    `session` é a sessão do banco local: o controller grava a auditoria nela, para que
    alteração e auditoria entrem no mesmo commit.
    """

    session: AsyncSession

    @abstractmethod
    async def listar(self) -> List[Dict[str, Any]]:
        """Lista todos os usuários autorizados (ativos e inativos)."""

    @abstractmethod
    async def buscar(self, username: str) -> Optional[Dict[str, Any]]:
        """Busca um usuário pelo login normalizado; None se não existir."""

    @abstractmethod
    async def inserir(self, username: str, nome: Optional[str], perfil: str, agora: datetime) -> None:
        """Inclui um usuário ativo. Não faz commit."""

    @abstractmethod
    async def atualizar(self, username: str, perfil: str, ativo: bool, agora: datetime) -> None:
        """Altera perfil e situação. Não faz commit."""

    @abstractmethod
    async def commit(self) -> None:
        """Confirma a transação (alteração + auditoria juntas)."""

    @abstractmethod
    async def rollback(self) -> None:
        """Desfaz a transação."""
