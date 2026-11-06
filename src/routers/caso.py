"""Endpoints HTTP do módulo de Casos (/api/casos).

Router sem lógica de negócio: valida entrada (Pydantic), injeta dependências
e delega ao Controller. Protegido por padrão (Default-Private Router Pattern).
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..auth.auth import auth_handler
from ..controllers import caso_controller
from ..dependencies import get_aghu_solicitacao_provider, get_caso_provider
from ..providers.implementations.aghu_solicitacao_postgres_provider import AghuSolicitacaoPostgresProvider
from ..providers.implementations.caso_postgres_provider import CasoPostgresProvider

router = APIRouter(
    prefix="/api/casos",
    tags=["Casos"],
    dependencies=[Depends(auth_handler.decode_token)],
)


class AbrirCasoIn(BaseModel):
    """Corpo de POST /api/casos."""
    solicitacao_aghu: str = Field(..., min_length=1, max_length=20)
    tipo_exame: str = Field(..., min_length=2, max_length=3, description="HP, CO, CG ou CCV")


class EncaminharIn(BaseModel):
    """Corpo de POST /api/casos/{id}/encaminhar."""
    destino: str = Field(..., min_length=1, max_length=30)
    motivo: str = Field(..., min_length=1, max_length=500)


class RetornarIn(BaseModel):
    """Corpo de POST /api/casos/{id}/retornar."""
    motivo: str = Field(..., min_length=1, max_length=500)


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.get("", response_model=Dict[str, Any])
async def buscar_casos(
    solicitacao: Optional[str] = None,
    paciente: Optional[str] = None,
    identificador: Optional[str] = None,
    tipo_exame: Optional[str] = None,
    etapa: Optional[str] = None,
    status: Optional[str] = None,
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    provider: CasoPostgresProvider = Depends(get_caso_provider),
):
    """UC019 / RF027: busca paginada com filtros."""
    filtros = {
        "solicitacao": solicitacao, "paciente": paciente, "identificador": identificador,
        "tipo_exame": tipo_exame, "etapa": etapa, "status": status,
    }
    return await caso_controller.listar_casos(filtros, pagina, limite, provider)


@router.post("", response_model=Dict[str, Any], status_code=201)
async def abrir_caso(
    dados: AbrirCasoIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoPostgresProvider = Depends(get_caso_provider),
    aghu: AghuSolicitacaoPostgresProvider = Depends(get_aghu_solicitacao_provider),
):
    """UC002 / RF004: cria o caso a partir da solicitação do AGHU."""
    return await caso_controller.abrir_caso(
        dados.solicitacao_aghu, dados.tipo_exame, usuario, _ip(request), provider, aghu
    )


# Rotas fixas ANTES de /{caso_id} para não serem capturadas como parâmetro.
@router.get("/aghu/solicitacao/{solicitacao}", response_model=Dict[str, Any])
async def consultar_solicitacao(
    solicitacao: str,
    provider: CasoPostgresProvider = Depends(get_caso_provider),
    aghu: AghuSolicitacaoPostgresProvider = Depends(get_aghu_solicitacao_provider),
):
    """RF003: pré-visualiza paciente/amostras do AGHU (somente leitura)."""
    return await caso_controller.consultar_solicitacao_aghu(solicitacao, provider, aghu)


@router.get("/{caso_id}", response_model=Dict[str, Any])
async def obter_caso(
    caso_id: int,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoPostgresProvider = Depends(get_caso_provider),
):
    return await caso_controller.obter_caso(caso_id, usuario, provider)


@router.get("/{caso_id}/historico", response_model=List[Dict[str, Any]])
async def historico(
    caso_id: int,
    provider: CasoPostgresProvider = Depends(get_caso_provider),
):
    """UC018 / RF021: linha do tempo do caso."""
    return await caso_controller.historico_caso(caso_id, provider)


@router.post("/{caso_id}/concluir-etapa", response_model=Dict[str, Any])
async def concluir_etapa(
    caso_id: int,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoPostgresProvider = Depends(get_caso_provider),
):
    """UC017 / RF019: conclui a etapa atual com validação."""
    return await caso_controller.concluir_etapa(caso_id, usuario, _ip(request), provider)


@router.post("/{caso_id}/encaminhar", response_model=Dict[str, Any])
async def encaminhar(
    caso_id: int,
    dados: EncaminharIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoPostgresProvider = Depends(get_caso_provider),
):
    """UC012 / RF015: encaminha o caso (motivo obrigatório)."""
    return await caso_controller.encaminhar_caso(caso_id, dados.destino, dados.motivo, usuario, _ip(request), provider)


@router.post("/{caso_id}/retornar", response_model=Dict[str, Any])
async def retornar(
    caso_id: int,
    dados: RetornarIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoPostgresProvider = Depends(get_caso_provider),
):
    """UC012 / RF015: devolve o caso à etapa de origem (motivo obrigatório)."""
    return await caso_controller.retornar_caso(caso_id, dados.motivo, usuario, _ip(request), provider)