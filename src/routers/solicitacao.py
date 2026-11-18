"""Endpoints HTTP do módulo de Solicitações (/api/solicitacoes).

Router sem lógica de negócio: valida entrada e saída (Pydantic), injeta dependências
e delega ao Controller. Protegido por padrão (Default-Private Router Pattern).
"""
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field, ConfigDict

from ..auth.auth import auth_handler
from ..controllers import solicitacao_controller
from ..dependencies import get_aghu_solicitacao_provider, get_solicitacao_provider
from ..providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface
from ..providers.interfaces.solicitacao_provider_interface import SolicitacaoProviderInterface

router = APIRouter(
    prefix="/api/solicitacoes",
    tags=["Solicitações de Exames"],
    dependencies=[Depends(auth_handler.decode_token)],
)

#: Números do AGHU chegam como inteiro do AGHU ou texto do banco local.
NumeroAghu = Union[int, str]


# --- Entrada ------------------------------------------------------------------
class AbrirSolicitacaoIn(BaseModel):
    """Somente vínculo AGHU; cliente não pode declarar nem sobrescrever tipo de exame."""
    model_config = ConfigDict(extra="forbid")
    solicitacao_aghu: str = Field(..., min_length=1, max_length=20)


class EncaminharIn(BaseModel):
    """Corpo de POST /api/solicitacoes/{id}/encaminhar."""
    destino: str = Field(..., min_length=1, max_length=30)
    motivo: str = Field(..., min_length=1, max_length=500)


class RetornarIn(BaseModel):
    """Corpo de POST /api/solicitacoes/{id}/retornar."""
    motivo: str = Field(..., min_length=1, max_length=500)


# --- Saída --------------------------------------------------------------------
class SolicitacaoResumo(BaseModel):
    """Solicitação na lista da busca."""
    id: int
    identificador_interno: str
    solicitacao_aghu: NumeroAghu
    paciente_nome: str
    tipo_exame: str
    etapa_atual: str
    status: str
    criado_em: str
    atualizado_em: str
    urgente: Optional[bool] = None
    retirado_em: Optional[str] = None
    retirado_por: Optional[str] = None


class PaginaBuscaSolicitacoes(BaseModel):
    """Página da busca de solicitações."""
    items: List[SolicitacaoResumo]
    total: int
    pagina: int
    limite: int


class AmostraSolicitacao(BaseModel):
    """Amostra do AGHU vinculada à solicitação."""
    id: int
    solicitacao_id: int
    amostra_aghu: NumeroAghu
    descricao: Optional[str] = None


class AcoesSolicitacao(BaseModel):
    """Ações que o perfil do usuário pode executar na etapa atual."""
    pode_concluir: bool
    pode_retornar: bool
    destinos_encaminhamento: List[str]


class SolicitacaoDetalhe(SolicitacaoResumo):
    """Solicitação aberta, com amostras e ações permitidas."""
    paciente_codigo_aghu: NumeroAghu
    prontuario_aghu: Optional[NumeroAghu] = None
    ultima_sincronizacao_aghu: Optional[str] = None
    criado_por: str
    amostras: List[AmostraSolicitacao]
    acoes: AcoesSolicitacao


class AmostraAghu(BaseModel):
    """Amostra da solicitação, como vem do AGHU."""
    amostra_aghu: NumeroAghu
    descricao: Optional[str] = None


class SolicitacaoAghu(BaseModel):
    """Pré-visualização da solicitação do AGHU antes de abri-la no SAP."""
    solicitacao_aghu: NumeroAghu
    paciente_codigo_aghu: NumeroAghu
    paciente_nome: str
    prontuario_aghu: Optional[NumeroAghu] = None
    tipo_exame: Optional[str] = None
    amostras: List[AmostraAghu]
    solicitacao_existente: Optional[str] = None


class Movimentacao(BaseModel):
    """Movimentação da solicitação (histórico)."""
    id: int
    solicitacao_id: int
    tipo: str
    etapa_origem: Optional[str] = None
    etapa_destino: Optional[str] = None
    motivo: Optional[str] = None
    usuario: str
    criado_em: str


def _ip(request: Request) -> Optional[str]:
    """IP de origem para a auditoria (sem confiar em X-Forwarded-For)."""
    return request.client.host if request.client else None


@router.get("/busca", response_model=PaginaBuscaSolicitacoes)
async def buscar_solicitacoes(
    solicitacao: Optional[str] = Query(None, description="Número da solicitação no AGHU (código do exame)"),
    prontuario: Optional[str] = Query(None, max_length=20, description="Prontuário do paciente (busca exata)"),
    identificador: Optional[str] = None,
    tipo_exame: Optional[str] = None,
    etapa: Optional[str] = None,
    status: Optional[str] = None,
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """UC019 / RF027: busca paginada com filtros."""
    filtros = {
        "solicitacao": solicitacao, "prontuario": prontuario, "identificador": identificador,
        "tipo_exame": tipo_exame, "etapa": etapa, "status": status,
    }
    return await solicitacao_controller.buscar_solicitacoes(filtros, pagina, limite, provider)


@router.post("", response_model=SolicitacaoDetalhe, status_code=status.HTTP_201_CREATED)
async def abrir_solicitacao(
    dados: AbrirSolicitacaoIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
    aghu: AghuSolicitacaoProviderInterface = Depends(get_aghu_solicitacao_provider),
) -> Dict[str, Any]:
    """UC002 / RF004: abre no SAP a solicitação recebida no AGHU."""
    return await solicitacao_controller.abrir_solicitacao(
        dados.solicitacao_aghu, usuario, _ip(request), provider, aghu
    )


# Rotas fixas ANTES de /{solicitacao_id} para não serem capturadas como parâmetro.
@router.get("/aghu/solicitacao/{numero_aghu}", response_model=SolicitacaoAghu)
async def consultar_solicitacao(
    numero_aghu: str,
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
    aghu: AghuSolicitacaoProviderInterface = Depends(get_aghu_solicitacao_provider),
) -> Dict[str, Any]:
    """RF003: pré-visualiza paciente/amostras do AGHU (somente leitura)."""
    return await solicitacao_controller.consultar_solicitacao_aghu(numero_aghu, provider, aghu)


class ConferenciaAghu(BaseModel):
    """Diferenças entre os dados cifrados na solicitação e o cadastro oficial."""
    solicitacao_id: int
    atualizacao_pendente: bool
    divergencias: Dict[str, Dict[str, Optional[str]]]
    ultima_sincronizacao_aghu: Optional[str] = None
    pode_sincronizar: bool


@router.get("/{solicitacao_id}/conferencia-aghu", response_model=ConferenciaAghu)
async def conferencia_aghu(
    solicitacao_id: int,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
    aghu: AghuSolicitacaoProviderInterface = Depends(get_aghu_solicitacao_provider),
) -> Dict[str, Any]:
    """Compara a cópia cadastral local com o AGHU (somente leitura)."""
    return await solicitacao_controller.conferir_dados_aghu(solicitacao_id, usuario, provider, aghu)


@router.post("/{solicitacao_id}/sincronizar-aghu", response_model=SolicitacaoDetalhe)
async def sincronizar_aghu(
    solicitacao_id: int,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
    aghu: AghuSolicitacaoProviderInterface = Depends(get_aghu_solicitacao_provider),
) -> Dict[str, Any]:
    """Sincroniza somente nome/prontuário no banco SAP, com histórico e auditoria."""
    return await solicitacao_controller.sincronizar_dados_aghu(solicitacao_id, usuario, _ip(request), provider, aghu)


@router.get("/{solicitacao_id}", response_model=SolicitacaoDetalhe)
async def obter_solicitacao(
    solicitacao_id: int,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """Detalhe da solicitação, com amostras e as ações permitidas ao perfil."""
    return await solicitacao_controller.obter_solicitacao(solicitacao_id, usuario, provider)


@router.get("/{solicitacao_id}/historico", response_model=List[Movimentacao])
async def historico(
    solicitacao_id: int,
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> List[Dict[str, Any]]:
    """UC018 / RF021: linha do tempo da solicitação."""
    return await solicitacao_controller.historico_solicitacao(solicitacao_id, provider)


@router.post("/{solicitacao_id}/concluir-etapa", response_model=SolicitacaoDetalhe)
async def concluir_etapa(
    solicitacao_id: int,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """UC017 / RF019: conclui a etapa atual com validação."""
    return await solicitacao_controller.concluir_etapa(solicitacao_id, usuario, _ip(request), provider)


@router.post("/{solicitacao_id}/encaminhar", response_model=SolicitacaoDetalhe)
async def encaminhar(
    solicitacao_id: int,
    dados: EncaminharIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """UC012 / RF015: encaminha a solicitação (motivo obrigatório)."""
    return await solicitacao_controller.encaminhar_solicitacao(solicitacao_id, dados.destino, dados.motivo, usuario, _ip(request), provider)


@router.post("/{solicitacao_id}/retornar", response_model=SolicitacaoDetalhe)
async def retornar(
    solicitacao_id: int,
    dados: RetornarIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: SolicitacaoProviderInterface = Depends(get_solicitacao_provider),
) -> Dict[str, Any]:
    """UC012 / RF015: devolve a solicitação à etapa de origem (motivo obrigatório)."""
    return await solicitacao_controller.retornar_solicitacao(solicitacao_id, dados.motivo, usuario, _ip(request), provider)
