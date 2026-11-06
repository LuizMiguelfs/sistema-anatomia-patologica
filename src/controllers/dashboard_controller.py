from src.models.dashboard import DashboardResumoResponse
from src.providers.interfaces.dashboard_provider_interface import (DashboardProviderInterface,)


async def obter_resumo_dashboard(
    provider: DashboardProviderInterface, #! pega do Interface e não do Demo por causa da injeção de dependencia
    ) -> DashboardResumoResponse:
    """Obtém o resumo operacional e gerencial do dashboard."""
    return await provider.obter_resumo()
