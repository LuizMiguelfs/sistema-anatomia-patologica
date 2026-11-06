from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from starlette.concurrency import run_in_threadpool

from ..auth.auth import auth_handler

from datetime import date, datetime
from typing import Any, Dict, Literal, Optional
from fastapi import Query
from ..controllers import auditoria_controller
from ..dependencies import get_auditoria_provider
from ..providers.interfaces.auditoria_provider_interface import AuditoriaProviderInterface

router = APIRouter(
    prefix="/api",
    tags=["Admin"],
    dependencies=[Depends(auth_handler.decode_token)],
)

class AdminData(BaseModel):
    message: str
    user_groups: List[str]

async def verify_admin_group(current_user: dict = Depends(auth_handler.decode_token)):
    ADMIN_GROUP = "GLO-SEC-HCPE-SETISD"
    if ADMIN_GROUP not in current_user.get("groups", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user

@router.get("/admin-only-data", response_model=AdminData)
async def get_admin_data(current_user: dict = Depends(verify_admin_group)):
    """
    Returns data only accessible by users with admin privileges.
    """
    return AdminData(
        message="This is highly confidential admin data!",
        user_groups=current_user.get("groups", [])
    )

class ADUserSearchResponse(BaseModel):
    exists: bool
    username: str
    displayName: str
    email: str
    department: str

async def verify_ad_search_access(current_user: dict = Depends(auth_handler.decode_token)) -> dict:
    """
    Busca no AD: TI (grupo do AD) e Chefia (perfil local). A busca é o primeiro passo da
    gestão de usuários (decidir quem entra no SAP e com qual perfil), que é da Chefia.
    """
    if "GLO-SEC-HCPE-SETISD" in current_user.get("groups", []) or current_user.get("role") == "CHEFIA":
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")


@router.get("/admin/ad-user-search/{username}", response_model=ADUserSearchResponse)
async def search_ad_user(username: str, current_user: dict = Depends(verify_ad_search_access)):
    """
    Busca e valida um usuário no Active Directory (ou Mock) pelo login de rede.
    Restrito à TI (grupo do AD) e à Chefia (gestão de usuários).
    """
    res = await run_in_threadpool(auth_handler.search_ad_user, username)
    return ADUserSearchResponse(**res)


# ------------------------------------------------------------------------------
# Trilha de auditoria (consulta administrativa)
# ------------------------------------------------------------------------------
# Quem pode consultar: TI (grupo GLO-SEC-HCPE-SETISD do AD) e a Chefia (perfil local CHEFIA).
# O perfil local passa a existir com o módulo de autenticação (Membro 1); até lá, apenas a TI.
GRUPO_TI = "GLO-SEC-HCPE-SETISD"
PERFIL_CHEFIA = "CHEFIA"

CategoriaAuditoria = Literal["SEGURANCA", "NEGOCIO_CLINICO", "CONFIGURACAO"]


async def verify_auditoria_access(current_user: dict = Depends(auth_handler.decode_token)) -> dict:
    """Permite a consulta da trilha à TI (grupo do AD) ou à Chefia (perfil local)."""
    if GRUPO_TI in current_user.get("groups", []) or current_user.get("role") == PERFIL_CHEFIA:
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para consultar a auditoria.")


class AuditLogSaida(BaseModel):
    """Registro de auditoria como retornado pela API (dados antes/depois já como objetos)."""
    id: int
    created_at: datetime
    usuario: str
    categoria: str
    acao: str
    recurso: str
    dados_anteriores: Optional[Any] = None
    dados_novos: Optional[Any] = None
    ip_origem: Optional[str] = None


class PaginaAuditoria(BaseModel):
    """Página da consulta administrativa da trilha de auditoria."""
    total: int
    limite: int
    offset: int
    itens: List[AuditLogSaida]


@router.get("/admin/auditoria", response_model=PaginaAuditoria)
async def listar_auditoria(
    usuario: Optional[str] = Query(None, max_length=128, description="Login exato do usuário"),
    categoria: Optional[CategoriaAuditoria] = Query(None),
    acao: Optional[str] = Query(None, max_length=100, description="Ação exata, ex.: CRIAR_PACIENTE"),
    recurso: Optional[str] = Query(None, max_length=200, description="Exato (paciente:123) ou prefixo com * (paciente:*)"),
    data_inicio: Optional[date] = Query(None, description="Dia inicial (no fuso informado), inclusivo"),
    data_fim: Optional[date] = Query(None, description="Dia final (no fuso informado), inclusivo"),
    utc_offset_minutos: int = Query(0, ge=-720, le=840, description="Fuso de quem consulta, em minutos (Recife = -180)"),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: AuditoriaProviderInterface = Depends(get_auditoria_provider),
    current_user: dict = Depends(verify_auditoria_access),
) -> Dict[str, Any]:
    """Consulta a trilha de auditoria com filtros e paginação (mais recentes primeiro)."""
    return await auditoria_controller.listar_logs(
        provider,
        usuario=usuario,
        categoria=categoria,
        acao=acao,
        recurso=recurso,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limite=limite,
        offset=offset,
        utc_offset_minutos=utc_offset_minutos,
    )
