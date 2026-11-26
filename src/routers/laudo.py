"""Revisão de pré-laudos, marcadores fictícios de liberação e arquivamento (T08)."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request

from ..auth.auth import auth_handler
from ..controllers import laudo_controller
from ..dependencies import get_solicitacao_provider
from ..providers.interfaces.solicitacao_provider_interface import SolicitacaoProviderInterface

router = APIRouter(prefix="/api/laudos", tags=["Revisão e laudos"],
                   dependencies=[Depends(auth_handler.decode_token)])


def _ip(request: Request) -> Optional[str]:
    """Origem da requisição para auditoria; não confia em cabeçalhos de proxy arbitrários."""
    return request.client.host if request.client else None


@router.get("/revisoes")
async def listar_revisoes(
    limite: int = Query(100, ge=1, le=100), deslocamento: int = Query(0, ge=0),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> List[Dict[str, Any]]:
    """Fila de rascunhos/pré-laudos aguardando atuação clínica."""
    return await laudo_controller.fila_revisoes(provider, limite, deslocamento)


@router.get("/pendentes-liberacao")
async def listar_pendentes_liberacao(
    limite: int = Query(100, ge=1, le=100), deslocamento: int = Query(0, ge=0),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> List[Dict[str, Any]]:
    """Laudos validados e pendentes de liberação ou arquivamento."""
    return await provider.listar_pendentes_liberacao(limite, deslocamento)


@router.get("/solicitacoes/{solicitacao_id}")
async def consultar(solicitacao_id: int, provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider)) -> Dict[str, Any]:
    """Histórico de validações, liberação e laudos locais disponíveis para consulta."""
    return await laudo_controller.consultar_laudos(solicitacao_id, provider)


@router.post("/solicitacoes/{solicitacao_id}/liberacao-simulada")
async def registrar_liberacao_simulada(
    solicitacao_id: int, request: Request, usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """Evento FICTÍCIO do AGHU, autorizado apenas no modo demo com preceptoria."""
    return await laudo_controller.simular_liberacao(solicitacao_id, usuario, _ip(request), provider)


@router.post("/solicitacoes/{solicitacao_id}/arquivar")
async def arquivar(
    solicitacao_id: int, request: Request, usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """Arquivamento condicionado à liberação já registrada e com auditoria."""
    return await laudo_controller.arquivar_solicitacao(solicitacao_id, usuario, _ip(request), provider)
