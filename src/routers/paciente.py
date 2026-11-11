"""Consulta de pacientes, exclusivamente em fonte AGHU/CSV de leitura.

Não expõe POST/PUT/DELETE: cadastro e retificação pertencem ao AGHU/Regulação.
"""
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..auth.auth import auth_handler
from ..config import settings
from ..controllers import paciente_controller
from ..dependencies import get_paciente_provider
from ..providers.interfaces.paciente_provider_interface import PacienteProviderInterface

STRATEGY = settings.PACIENTE_PROVIDER_TYPE
router = APIRouter(
    prefix="/api/pacientes",
    tags=["Pacientes"],
    dependencies=[Depends(auth_handler.decode_token)],
)


class PacienteSaida(BaseModel):
    """Campos cadastrais do catálogo oficial, sem edição no SAP."""
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
    """Fonte e permissões de API (sempre somente leitura)."""
    fonte: str
    escrita: bool
    exclusao: bool


@router.get("/capacidades", response_model=CapacidadesSaida)
async def obter_capacidades(
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY)),
) -> Dict[str, Any]:
    """Identifica AGHU/CSV e informa impossibilidade de cadastro pelo SAP."""
    return paciente_controller.obter_capacidades(provider)


@router.get("", response_model=List[PacienteSaida])
async def listar_pacientes(
    termo: Optional[str] = Query(None, max_length=100, description="Nome (mín. 3 letras), código, CPF ou CNS"),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY)),
) -> List[Dict[str, Any]]:
    """Consulta pacientes (filtros e paginação), sem modificar a origem."""
    return await paciente_controller.listar_pacientes(provider, termo=termo, limite=limite, offset=offset)


@router.get("/{codigo}", response_model=PacienteSaida)
async def obter_paciente(
    codigo: int,
    provider: PacienteProviderInterface = Depends(get_paciente_provider(STRATEGY)),
) -> Dict[str, Any]:
    """Detalhes cadastrais por código AGHU."""
    return await paciente_controller.obter_paciente_por_codigo(codigo, provider)
