"""Endpoints HTTP do módulo de Casos (/api/casos).

Router sem lógica de negócio: valida entrada e saída (Pydantic), injeta dependências
e delega ao Controller. Protegido por padrão (Default-Private Router Pattern).
"""
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field, ConfigDict

from ..auth.auth import auth_handler
from ..controllers import caso_controller
from ..dependencies import get_aghu_solicitacao_provider, get_caso_provider
from ..providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface
from ..providers.interfaces.caso_provider_interface import CasoProviderInterface

router = APIRouter(
    prefix="/api/casos",
    tags=["Casos"],
    dependencies=[Depends(auth_handler.decode_token)],
)

#: Números do AGHU chegam como inteiro do AGHU ou texto do banco local.
NumeroAghu = Union[int, str]


# --- Entrada ------------------------------------------------------------------
class AbrirCasoIn(BaseModel):
    """Somente vínculo AGHU; cliente não pode declarar nem sobrescrever tipo de exame."""
    model_config = ConfigDict(extra="forbid")
    solicitacao_aghu: str = Field(..., min_length=1, max_length=20)


class EncaminharIn(BaseModel):
    """Corpo de POST /api/casos/{id}/encaminhar."""
    destino: str = Field(..., min_length=1, max_length=30)
    motivo: str = Field(..., min_length=1, max_length=500)


class RetornarIn(BaseModel):
    """Corpo de POST /api/casos/{id}/retornar."""
    motivo: str = Field(..., min_length=1, max_length=500)


# --- Saída --------------------------------------------------------------------
class CasoResumo(BaseModel):
    """Caso na lista da busca."""
    id: int
    identificador_interno: str
    solicitacao_aghu: NumeroAghu
    paciente_nome: str
    tipo_exame: str
    etapa_atual: str
    status: str
    criado_em: str
    atualizado_em: str


class PaginaCasos(BaseModel):
    """Página da busca de casos."""
    items: List[CasoResumo]
    total: int
    pagina: int
    limite: int


class AmostraCaso(BaseModel):
    """Amostra do AGHU vinculada ao caso."""
    id: int
    caso_id: int
    amostra_aghu: NumeroAghu
    descricao: Optional[str] = None


class AcoesCaso(BaseModel):
    """Ações que o perfil do usuário pode executar na etapa atual."""
    pode_concluir: bool
    pode_retornar: bool
    destinos_encaminhamento: List[str]


class CasoDetalhe(CasoResumo):
    """Caso aberto, com amostras e ações permitidas."""
    paciente_codigo_aghu: NumeroAghu
    prontuario_aghu: Optional[NumeroAghu] = None
    ultima_sincronizacao_aghu: Optional[str] = None
    criado_por: str
    amostras: List[AmostraCaso]
    acoes: AcoesCaso


class AmostraAghu(BaseModel):
    """Amostra da solicitação, como vem do AGHU."""
    amostra_aghu: NumeroAghu
    descricao: Optional[str] = None


class SolicitacaoAghu(BaseModel):
    """Pré-visualização da solicitação do AGHU antes de abrir o caso."""
    solicitacao_aghu: NumeroAghu
    paciente_codigo_aghu: NumeroAghu
    paciente_nome: str
    prontuario_aghu: Optional[NumeroAghu] = None
    tipo_exame: Optional[str] = None
    amostras: List[AmostraAghu]
    caso_existente: Optional[str] = None


class Movimentacao(BaseModel):
    """Movimentação do caso (histórico)."""
    id: int
    caso_id: int
    tipo: str
    etapa_origem: Optional[str] = None
    etapa_destino: Optional[str] = None
    motivo: Optional[str] = None
    usuario: str
    criado_em: str


def _ip(request: Request) -> Optional[str]:
    """IP de origem para a auditoria (sem confiar em X-Forwarded-For)."""
    return request.client.host if request.client else None


@router.get("", response_model=PaginaCasos)
async def buscar_casos(
    solicitacao: Optional[str] = Query(None, description="Número da solicitação no AGHU (código do exame)"),
    prontuario: Optional[str] = Query(None, max_length=20, description="Prontuário do paciente (busca exata)"),
    identificador: Optional[str] = None,
    tipo_exame: Optional[str] = None,
    etapa: Optional[str] = None,
    status: Optional[str] = None,
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """UC019 / RF027: busca paginada com filtros."""
    filtros = {
        "solicitacao": solicitacao, "prontuario": prontuario, "identificador": identificador,
        "tipo_exame": tipo_exame, "etapa": etapa, "status": status,
    }
    return await caso_controller.listar_casos(filtros, pagina, limite, provider)


@router.post("", response_model=CasoDetalhe, status_code=status.HTTP_201_CREATED)
async def abrir_caso(
    dados: AbrirCasoIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
    aghu: AghuSolicitacaoProviderInterface = Depends(get_aghu_solicitacao_provider),
) -> Dict[str, Any]:
    """UC002 / RF004: cria o caso a partir da solicitação do AGHU."""
    return await caso_controller.abrir_caso(
        dados.solicitacao_aghu, usuario, _ip(request), provider, aghu
    )


# Rotas fixas ANTES de /{caso_id} para não serem capturadas como parâmetro.
@router.get("/aghu/solicitacao/{solicitacao}", response_model=SolicitacaoAghu)
async def consultar_solicitacao(
    solicitacao: str,
    provider: CasoProviderInterface = Depends(get_caso_provider),
    aghu: AghuSolicitacaoProviderInterface = Depends(get_aghu_solicitacao_provider),
) -> Dict[str, Any]:
    """RF003: pré-visualiza paciente/amostras do AGHU (somente leitura)."""
    return await caso_controller.consultar_solicitacao_aghu(solicitacao, provider, aghu)


class ConferenciaAghu(BaseModel):
    """Diferenças entre os dados cifrados no caso e o cadastro oficial."""
    caso_id: int
    atualizacao_pendente: bool
    divergencias: Dict[str, Dict[str, Optional[str]]]
    ultima_sincronizacao_aghu: Optional[str] = None
    pode_sincronizar: bool


@router.get("/{caso_id}/conferencia-aghu", response_model=ConferenciaAghu)
async def conferencia_aghu(
    caso_id: int,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
    aghu: AghuSolicitacaoProviderInterface = Depends(get_aghu_solicitacao_provider),
) -> Dict[str, Any]:
    """Compara a cópia cadastral local com o AGHU (somente leitura)."""
    return await caso_controller.conferir_dados_aghu(caso_id, usuario, provider, aghu)


@router.post("/{caso_id}/sincronizar-aghu", response_model=CasoDetalhe)
async def sincronizar_aghu(
    caso_id: int,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
    aghu: AghuSolicitacaoProviderInterface = Depends(get_aghu_solicitacao_provider),
) -> Dict[str, Any]:
    """Sincroniza somente nome/prontuário no banco SAP, com histórico e auditoria."""
    return await caso_controller.sincronizar_dados_aghu(caso_id, usuario, _ip(request), provider, aghu)


@router.get("/{caso_id}", response_model=CasoDetalhe)
async def obter_caso(
    caso_id: int,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """Detalhe do caso, com amostras e as ações permitidas ao perfil."""
    return await caso_controller.obter_caso(caso_id, usuario, provider)


@router.get("/{caso_id}/historico", response_model=List[Movimentacao])
async def historico(
    caso_id: int,
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> List[Dict[str, Any]]:
    """UC018 / RF021: linha do tempo do caso."""
    return await caso_controller.historico_caso(caso_id, provider)


@router.post("/{caso_id}/concluir-etapa", response_model=CasoDetalhe)
async def concluir_etapa(
    caso_id: int,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """UC017 / RF019: conclui a etapa atual com validação."""
    return await caso_controller.concluir_etapa(caso_id, usuario, _ip(request), provider)


@router.post("/{caso_id}/encaminhar", response_model=CasoDetalhe)
async def encaminhar(
    caso_id: int,
    dados: EncaminharIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """UC012 / RF015: encaminha o caso (motivo obrigatório)."""
    return await caso_controller.encaminhar_caso(caso_id, dados.destino, dados.motivo, usuario, _ip(request), provider)


@router.post("/{caso_id}/retornar", response_model=CasoDetalhe)
async def retornar(
    caso_id: int,
    dados: RetornarIn,
    request: Request,
    usuario: Dict[str, Any] = Depends(auth_handler.decode_token),
    provider: CasoProviderInterface = Depends(get_caso_provider),
) -> Dict[str, Any]:
    """UC012 / RF015: devolve o caso à etapa de origem (motivo obrigatório)."""
    return await caso_controller.retornar_caso(caso_id, dados.motivo, usuario, _ip(request), provider)
