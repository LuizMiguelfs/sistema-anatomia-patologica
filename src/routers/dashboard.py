"""
Painel de indicadores (Membro 5): resumo exibido na tela inicial.
Protegido por padrão (Default-Private Router Pattern).
"""

from fastapi import APIRouter, Depends

from ..auth.auth import auth_handler
from ..controllers.dashboard_controller import obter_resumo_dashboard
from ..dependencies import get_dashboard_provider
from ..models.dashboard import DashboardResumoResponse
from ..providers.interfaces.dashboard_provider_interface import DashboardProviderInterface

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(auth_handler.decode_token)],
)


@router.get(
    "/resumo",
    response_model=DashboardResumoResponse,
    summary="Consultar resumo do dashboard",
)
async def consultar_resumo_dashboard(
    provider: DashboardProviderInterface = Depends(get_dashboard_provider),
) -> DashboardResumoResponse:
    """Resumo de indicadores do painel (o provedor atual é demonstrativo)."""
    return await obter_resumo_dashboard(provider)
