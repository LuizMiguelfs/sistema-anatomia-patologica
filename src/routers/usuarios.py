"""
Gestão de usuários do SAP (RF028 / UC026): quem acessa o sistema e com qual perfil.
Restrita ao perfil CHEFIA. Sem rota de exclusão: o acesso é inativado, nunca apagado.
"""

from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from ..auth.auth import auth_handler
from ..controllers import usuario_controller
from ..dependencies import get_usuario_provider
from ..providers.interfaces.usuario_provider_interface import UsuarioProviderInterface

PerfilSAP = Literal["RECEPCAO", "LABORATORIO", "RESIDENTE", "PRECEPTORIA", "CHEFIA"]

router = APIRouter(
    prefix="/api/admin/usuarios",
    tags=["Usuários"],
    dependencies=[Depends(auth_handler.decode_token)],
)

somente_chefia = auth_handler.require_roles("CHEFIA")


class UsuarioSaida(BaseModel):
    """Usuário autorizado como retornado pela API."""
    username: str
    nome: Optional[str] = None
    perfil: str
    ativo: bool
    criado_em: datetime
    atualizado_em: Optional[datetime] = None


class NovoUsuario(BaseModel):
    """Inclusão: login de rede (validado no AD) e perfil."""
    username: str = Field(..., min_length=1, max_length=128)
    perfil: PerfilSAP


class TrocaPerfil(BaseModel):
    """Novo perfil do usuário."""
    perfil: PerfilSAP


class TrocaSituacao(BaseModel):
    """True reativa, False inativa."""
    ativo: bool


def _ip(request: Request) -> Optional[str]:
    """IP de origem para a auditoria (sem confiar em X-Forwarded-For)."""
    return request.client.host if request.client else None


@router.get("", response_model=List[UsuarioSaida])
async def listar_usuarios(
    provider: UsuarioProviderInterface = Depends(get_usuario_provider),
    current_user: dict = Depends(somente_chefia),
):
    """Lista os usuários autorizados no SAP (ativos e inativos)."""
    return await usuario_controller.listar_usuarios(provider)


@router.post("", response_model=UsuarioSaida, status_code=status.HTTP_201_CREATED)
async def incluir_usuario(
    dados: NovoUsuario,
    request: Request,
    provider: UsuarioProviderInterface = Depends(get_usuario_provider),
    current_user: dict = Depends(somente_chefia),
):
    """Autoriza um login do AD no SAP com o perfil escolhido."""
    return await usuario_controller.incluir_usuario(
        provider, auth_handler.search_ad_user, current_user["username"], dados.username, dados.perfil, _ip(request)
    )


@router.patch("/{username}/perfil", response_model=UsuarioSaida)
async def alterar_perfil(
    username: str,
    dados: TrocaPerfil,
    request: Request,
    provider: UsuarioProviderInterface = Depends(get_usuario_provider),
    current_user: dict = Depends(somente_chefia),
):
    """Troca o perfil de um usuário (não vale para o próprio)."""
    return await usuario_controller.alterar_perfil(
        provider, auth_handler.search_ad_user, current_user["username"], username, dados.perfil, _ip(request)
    )


@router.patch("/{username}/situacao", response_model=UsuarioSaida)
async def alterar_situacao(
    username: str,
    dados: TrocaSituacao,
    request: Request,
    provider: UsuarioProviderInterface = Depends(get_usuario_provider),
    current_user: dict = Depends(somente_chefia),
):
    """Inativa ou reativa o acesso (não vale para o próprio)."""
    return await usuario_controller.alterar_situacao(
        provider, current_user["username"], username, dados.ativo, _ip(request)
    )
