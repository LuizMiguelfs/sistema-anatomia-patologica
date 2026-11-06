from abc import ABC, abstractmethod
from src.models.dashboard import DashboardResumoResponse

class DashboardProviderInterface(ABC):
    @abstractmethod #! obtem indicadores
    async def obter_resumo(self) -> DashboardResumoResponse: #! interface compativel com consultas assíncronas ao banco, e tbm garante que o metodo tenha um retorno definido
        """Obtém os indicadores operacionais e gerenciais."""