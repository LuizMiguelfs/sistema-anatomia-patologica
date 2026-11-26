"""Endpoints de Solicitações de Exames (/api/solicitacoes): "Não retirados" e "Retirados".

Router sem lógica de negócio: valida entrada e saída (Pydantic), injeta dependências e
delega ao Controller. Protegido por padrão (Default-Private Router Pattern).
"""
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from starlette.concurrency import run_in_threadpool

from ..auth.auth import auth_handler
from ..controllers import retirada_controller
from ..dependencies import get_solicitacao_provider
from ..providers.interfaces.solicitacao_provider_interface import SolicitacaoProviderInterface

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
    atualizado_em: Optional[str] = None
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


class CredencialResponsavel(BaseModel):
    """Comprovação de identidade do profissional, sem reutilizar a sessão da estação."""
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=1, max_length=4096)


async def _confirmar_responsavel(
    credencial: CredencialResponsavel, provider: SolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Reautentica contra AD/Mock, revalida cadastro local e exige perfil Recepção."""
    try:
        identidade = await run_in_threadpool(
            auth_handler.authenticate_user, credencial.username, credencial.password.get_secret_value()
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Autenticação corporativa indisponível") from None
    autorizado = await auth_handler.authorize_user(
        identidade["username"], identidade.get("groups", []), provider.session,
    )
    if autorizado.role != "RECEPCAO":
        raise HTTPException(403, "O responsável autenticado não possui o perfil Recepção")
    return {"username": identidade["username"], "role": autorizado.role}


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
    situacao: str = Query("NAO_RETIRADO", description="NAO_RETIRADO, RETIRADO ou ARQUIVADO"),
    tipo_exame: Optional[str] = None,
    de: Optional[str] = Query(None, description="Data inicial AAAA-MM-DD (recebimento ou retirada)"),
    ate: Optional[str] = Query(None, description="Data final AAAA-MM-DD"),
    busca: Optional[str] = Query(None, max_length=40, description="Prontuário, código AGHU ou código interno"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """Lista "Não retirados" ou "Retirados" com filtros."""
    filtros = {"tipo_exame": tipo_exame, "de": de, "ate": ate, "busca": busca}
    return await retirada_controller.listar_solicitacoes(situacao, filtros, pagina, limite, provider)


@router.post("/{solicitacao_id}/retirar", response_model=RetiradaOut)
async def retirar(
    solicitacao_id: int,
    request: Request,
    credencial: CredencialResponsavel,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """Recepção marca o material como retirado (encerra a etapa da Recepção)."""
    ator = await _confirmar_responsavel(credencial, provider)
    return await retirada_controller.marcar_retirado(
        solicitacao_id, ator, _ip(request), provider, estacao=str(usuario["username"])
    )


@router.post("/{solicitacao_id}/desfazer-retirada", response_model=RetiradaOut)
async def desfazer(
    solicitacao_id: int,
    request: Request,
    credencial: CredencialResponsavel,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """Recepção desfaz a retirada (volta para "Não retirados")."""
    ator = await _confirmar_responsavel(credencial, provider)
    return await retirada_controller.desfazer_retirada(
        solicitacao_id, ator, _ip(request), provider, estacao=str(usuario["username"])
    )
