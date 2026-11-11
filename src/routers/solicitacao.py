"""Endpoints de Solicitações de Exames (/api/solicitacoes): "Não retirados" e "Retirados".

Router sem lógica de negócio: valida entrada e saída (Pydantic), injeta dependências e
delega ao Controller. Protegido por padrão (Default-Private Router Pattern).
"""
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from ..auth.auth import auth_handler
from ..controllers import solicitacao_controller
from ..dependencies import get_caso_provider
from ..providers.interfaces.caso_provider_interface import CasoProviderInterface

router = APIRouter(
    prefix="/api/solicitacoes",
    tags=["Solicitações de Exames"],
    dependencies=[Depends(auth_handler.decode_token)],
)

NumeroAghu = Union[int, str]


class SolicitacaoItem(BaseModel):
    """Linha das listas "Não retirados" e "Retirados"."""
    id: int
    identificador_interno: str
    solicitacao_aghu: NumeroAghu
    paciente_nome: str
    prontuario_aghu: Optional[NumeroAghu] = None
    tipo_exame: str
    etapa_atual: str
    status: str
    urgente: bool
    criado_em: str
    retirado_em: Optional[str] = None
    retirado_por: Optional[str] = None
    qtd_amostras: int
    descricao_amostras: Optional[str] = None


class PaginaSolicitacoes(BaseModel):
    """Página de solicitações."""
    items: List[SolicitacaoItem]
    total: int
    pagina: int
    limite: int


class RetiradaOut(BaseModel):
    """Resultado de marcar ou desfazer a retirada."""
    id: int
    etapa_atual: str
    retirado_em: Optional[str] = None
    retirado_por: Optional[str] = None


def _ip(request: Request) -> Optional[str]:
    """IP de origem para a auditoria (sem confiar em X-Forwarded-For)."""
    return request.client.host if request.client else None


@router.get("", response_model=PaginaSolicitacoes)
async def listar(
    situacao: str = Query("NAO_RETIRADO", description="NAO_RETIRADO ou RETIRADO"),
    tipo_exame: Optional[str] = None,
    de: Optional[str] = Query(None, description="Data inicial AAAA-MM-DD (recebimento ou retirada)"),
    ate: Optional[str] = Query(None, description="Data final AAAA-MM-DD"),
    busca: Optional[str] = Query(None, max_length=40, description="Prontuário, código AGHU ou código interno"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """Lista "Não retirados" ou "Retirados" com filtros."""
    filtros = {"tipo_exame": tipo_exame, "de": de, "ate": ate, "busca": busca}
    return await solicitacao_controller.listar_solicitacoes(situacao, filtros, pagina, limite, provider)


@router.post("/{caso_id}/retirar", response_model=RetiradaOut)
async def retirar(
    caso_id: int,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """Recepção marca o material como retirado (encerra a etapa da Recepção)."""
    return await solicitacao_controller.marcar_retirado(caso_id, usuario, _ip(request), provider)


@router.post("/{caso_id}/desfazer-retirada", response_model=RetiradaOut)
async def desfazer(
    caso_id: int,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """Recepção desfaz a retirada (volta para "Não retirados")."""
    return await solicitacao_controller.desfazer_retirada(caso_id, usuario, _ip(request), provider)
