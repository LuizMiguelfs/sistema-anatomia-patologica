"""
Histórico de um recurso (RF021): linha do tempo das alterações de um caso, amostra etc.
Aberto a qualquer usuário autenticado; mostra só eventos NEGOCIO_CLINICO e não expõe IP.
A consulta administrativa completa da trilha fica em `admin.py` (/api/admin/auditoria).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..auth.auth import auth_handler
from ..controllers import auditoria_controller
from ..dependencies import get_auditoria_provider
from ..providers.interfaces.auditoria_provider_interface import AuditoriaProviderInterface

router = APIRouter(
    prefix="/api/auditoria",
    tags=["Auditoria"],
    dependencies=[Depends(auth_handler.decode_token)],
)


class HistoricoItem(BaseModel):
    """Evento do histórico de um recurso (sem IP de origem)."""
    id: int
    created_at: datetime
    usuario: str
    categoria: str
    acao: str
    recurso: str
    dados_anteriores: Optional[Any] = None
    dados_novos: Optional[Any] = None


class PaginaHistorico(BaseModel):
    """Página do histórico de um recurso."""
    total: int
    limite: int
    offset: int
    itens: List[HistoricoItem]


@router.get("/historico", response_model=PaginaHistorico)
async def historico(
    recurso: str = Query(..., min_length=3, max_length=200, pattern=r"^[A-Za-z_]+:.+$",
                         description="Recurso no formato tipo:identificador, ex.: caso:123"),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: AuditoriaProviderInterface = Depends(get_auditoria_provider),
) -> Dict[str, Any]:
    """Linha do tempo de um recurso, mais recentes primeiro."""
    return await auditoria_controller.historico_recurso(provider, recurso=recurso, limite=limite, offset=offset)
