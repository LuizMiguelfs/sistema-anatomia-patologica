from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AghuSolicitacaoProviderInterface(ABC):
    """
    Interface (contrato) de leitura de solicitações de exame no AGHU (RF003).
    Somente leitura (RNF005): nenhuma implementação pode escrever no AGHU.
    """

    @abstractmethod
    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Cabeçalho da solicitação (solicitação, código, nome e prontuário do paciente), ou None."""

    @abstractmethod
    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        """Amostras da solicitação (amostra_aghu, descricao)."""
