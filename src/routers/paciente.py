from datetime import date
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.auth import auth_handler
from ..config import settings
from ..controllers import paciente_controller
from ..dependencies import get_paciente_provider
from ..providers.interfaces.paciente_provider_interface import PacienteProviderInterface
from ..resources.database import get_app_db_session

# --- PONTO ÚNICO DE CONFIGURAÇÃO PARA ESTE ROTEADOR ---
# Definido por PACIENTE_PROVIDER_TYPE (POSTGRES | CSV) em src/config.py.
STRATEGY = settings.PACIENTE_PROVIDER_TYPE
# ----------------------------------------------------

router = APIRouter(
    prefix="/api/pacientes",
    tags=["Pacientes"],
    dependencies=[Depends(auth_handler.decode_token)]
)

Sexo = Literal["M", "F", "I"]
Cor = Literal["BRANCA", "PRETA", "PARDA", "AMARELA", "INDIGENA", "SEM_INFORMACAO"]


class PacienteEntrada(BaseModel):
    """Dados aceitos no cadastro e na edição de pacientes."""

    nome: str = Field(..., min_length=3, max_length=100)
    dt_nascimento: date
    sexo: Sexo
    cor: Optional[Cor] = None
    nome_mae: Optional[str] = Field(None, max_length=100)
    nome_pai: Optional[str] = Field(None, max_length=100)
    cpf: Optional[str] = Field(None, max_length=14, description="Com ou sem máscara")
    cns: Optional[str] = Field(None, max_length=18, description="Cartão Nacional de Saúde")

    @field_validator("nome", "nome_mae", "nome_pai", "cpf", "cns", mode="before")
    @classmethod
    def _limpar_texto(cls, valor: Optional[str]) -> Optional[str]:
        """Remove espaços nas pontas e converte string vazia em None."""
        if isinstance(valor, str):
            valor = valor.strip()
            return valor or None
        return valor

    @field_validator("sexo", "cor", mode="before")
    @classmethod
    def _maiusculo(cls, valor: Optional[str]) -> Optional[str]:
        """Aceita 'm'/'parda' etc. convertendo para maiúsculas."""
        if isinstance(valor, str):
            valor = valor.strip().upper()
            return valor or None
        return valor


class PacienteSaida(BaseModel):
    """Paciente retornado pela API (mesmo formato para CSV e AGHU)."""

    codigo: int
    nome: str
    dt_nascimento: Optional[date] = None
    sexo: Optional[str] = None
    cor: Optional[str] = None
    nome_mae: Optional[str] = None
    nome_pai: Optional[str] = None
    cpf: Optional[str] = None
    cns: Optional[str] = None


class CapacidadesSaida(BaseModel):
    """Fonte de dados ativa e operações permitidas."""

    fonte: str
    escrita: bool
    exclusao: bool


def _usuario(current_user: dict) -> str:
    """Login do usuário autenticado (claim `sub` do JWT)."""
    return current_user.get("sub") or current_user.get("username") or "desconhecido"


def _ip(request: Request) -> Optional[str]:
    """IP de origem da requisição, para a trilha de auditoria."""
    return request.client.host if request.client else None


@router.get("/capacidades", response_model=CapacidadesSaida)
async def obter_capacidades(
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY))
) -> Dict[str, Any]:
    """Informa a fonte de dados ativa (CSV/POSTGRES) e se ela permite escrita e exclusão."""
    return paciente_controller.obter_capacidades(provider)


@router.get("", response_model=List[PacienteSaida])
async def listar_pacientes(
    termo: Optional[str] = Query(None, max_length=100, description="Nome (mín. 3 letras), código, CPF ou CNS"),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY))
) -> List[Dict[str, Any]]:
    """Lista pacientes ativos com busca opcional e paginação (`limite`/`offset`)."""
    return await paciente_controller.listar_pacientes(provider, termo=termo, limite=limite, offset=offset)


@router.get("/{codigo}", response_model=PacienteSaida)
async def obter_paciente(
    codigo: int,
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY))
) -> Dict[str, Any]:
    """Obtém um paciente pelo código."""
    return await paciente_controller.obter_paciente_por_codigo(codigo, provider)


@router.post("", response_model=PacienteSaida, status_code=status.HTTP_201_CREATED)
async def criar_paciente(
    payload: PacienteEntrada,
    request: Request,
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY)),
    db: AsyncSession = Depends(get_app_db_session),
    current_user: dict = Depends(auth_handler.decode_token),
) -> Dict[str, Any]:
    """Cadastra um paciente (registra auditoria NEGOCIO_CLINICO)."""
    return await paciente_controller.criar_paciente(
        payload.model_dump(), provider, db, usuario=_usuario(current_user), ip_origem=_ip(request)
    )


@router.put("/{codigo}", response_model=PacienteSaida)
async def atualizar_paciente(
    codigo: int,
    payload: PacienteEntrada,
    request: Request,
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY)),
    db: AsyncSession = Depends(get_app_db_session),
    current_user: dict = Depends(auth_handler.decode_token),
) -> Dict[str, Any]:
    """Atualiza um paciente (auditoria com estado anterior e novo)."""
    return await paciente_controller.atualizar_paciente(
        codigo, payload.model_dump(), provider, db, usuario=_usuario(current_user), ip_origem=_ip(request)
    )


@router.delete("/{codigo}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_paciente(
    codigo: int,
    request: Request,
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY)),
    db: AsyncSession = Depends(get_app_db_session),
    current_user: dict = Depends(auth_handler.decode_token),
) -> Response:
    """Exclusão lógica do paciente (o registro é preservado; auditoria registrada)."""
    await paciente_controller.excluir_paciente(
        codigo, provider, db, usuario=_usuario(current_user), ip_origem=_ip(request)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
