from fastapi import APIRouter, Depends
from ..auth.auth import auth_handler
from src.controllers.dashboard_controller import obter_resumo_dashboard
from src.models.dashboard import DashboardResumoResponse
from src.providers.implementations.dashboard_demo_provider import (DashboardDemoProvider,)
from src.providers.interfaces.dashboard_provider_interface import (DashboardProviderInterface,)

#! endpoints do msm modulo organizados com o msm caminho inicial
router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(auth_handler.decode_token)], #! reutiliza a autenticação JWT
)

#! função pra injeção de dependencia (depois vai retornar algo de SQL)
def get_dashboard_provider() -> DashboardProviderInterface:
    return DashboardDemoProvider()

@router.get(
    "/resumo",
    response_model=DashboardResumoResponse, #* FastAPI valida e documenta a resposta 
    summary="Consultar resumo do dashboard",
)

async def consultar_resumo_dashboard(provider: DashboardProviderInterface = Depends(get_dashboard_provider),) -> DashboardResumoResponse:
    return await obter_resumo_dashboard(provider)