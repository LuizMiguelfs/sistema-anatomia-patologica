"""Endpoints das fases do setor (/api/fases): fila e formulário de cada fase.

Router sem lógica de negócio: valida entrada e saída (Pydantic), injeta dependências e
delega ao Controller. Protegido por padrão (Default-Private Router Pattern).
"""
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..auth.auth import auth_handler
from ..controllers import fase_controller
from ..dependencies import get_caso_provider
from ..providers.interfaces.caso_provider_interface import CasoProviderInterface

router = APIRouter(
    prefix="/api/fases",
    tags=["Fases do setor"],
    dependencies=[Depends(auth_handler.decode_token)],
)

NumeroAghu = Union[int, str]
ValorCampo = Union[bool, int, str, None]


class FormularioIn(BaseModel):
    """Valores do formulário da fase (nome do campo -> valor)."""
    dados: Dict[str, ValorCampo] = Field(default_factory=dict)


class ItemFila(BaseModel):
    """Solicitação na fila da fase (pendente ou concluída recente)."""
    id: int
    identificador_interno: str
    solicitacao_aghu: NumeroAghu
    paciente_nome: str
    prontuario_aghu: Optional[NumeroAghu] = None
    tipo_exame: str
    etapa_atual: str
    urgente: bool
    pendente: bool
    situacao_fase: Optional[str] = None
    entrou_em: Optional[str] = None
    salvo_em: Optional[str] = None
    salvo_por: Optional[str] = None
    concluido_em: Optional[str] = None
    concluido_por: Optional[str] = None
    editavel_ate: Optional[str] = None
    qtd_amostras: int
    descricao_amostras: Optional[str] = None


class PaginaFila(BaseModel):
    """Página da fila da fase."""
    items: List[ItemFila]
    total: int
    pagina: int
    limite: int


def _ip(request: Request) -> Optional[str]:
    """IP de origem para a auditoria (sem confiar em X-Forwarded-For)."""
    return request.client.host if request.client else None


@router.get("")
async def formularios() -> List[Dict[str, Any]]:
    """Definições das fases, perfis e campos dos formulários (provisórias)."""
    return fase_controller.formularios()


@router.get("/{etapa}/fila", response_model=PaginaFila)
async def fila(
    etapa: str,
    tipo_exame: Optional[str] = None,
    busca: Optional[str] = Query(None, max_length=40, description="Prontuário, código AGHU ou código interno"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(50, ge=1, le=100),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """Pendentes da fase e concluídas recentes ainda editáveis."""
    return await fase_controller.listar_fila(etapa, {"tipo_exame": tipo_exame, "busca": busca}, pagina, limite, provider)


@router.get("/{etapa}/solicitacoes/{caso_id}")
async def obter(
    etapa: str,
    caso_id: int,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """Formulário da fase para a solicitação, com permissões do perfil."""
    return await fase_controller.obter_fase(etapa, caso_id, usuario, provider)


@router.put("/{etapa}/solicitacoes/{caso_id}")
async def salvar(
    etapa: str,
    caso_id: int,
    corpo: FormularioIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """Salvar: grava o formulário sem exigir os campos obrigatórios."""
    return await fase_controller.salvar_fase(etapa, caso_id, corpo.dados, usuario, _ip(request), provider)


@router.post("/{etapa}/solicitacoes/{caso_id}/concluir")
async def concluir(
    etapa: str,
    caso_id: int,
    corpo: FormularioIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """Concluído: exige os obrigatórios e envia a solicitação para a próxima fase."""
    return await fase_controller.concluir_fase(etapa, caso_id, corpo.dados, usuario, _ip(request), provider)
