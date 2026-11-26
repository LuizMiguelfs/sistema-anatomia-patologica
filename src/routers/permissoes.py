"""Consulta autenticada da matriz inicial de permissões (T05)."""
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends
from ..auth.auth import ENV, MockAuthProvider, auth_handler
from ..helpers.matriz_permissoes import capacidades_do_perfil, matriz_inicial

router = APIRouter(prefix="/api/permissoes", tags=["Permissões"], dependencies=[Depends(auth_handler.decode_token)])


@router.get("")
async def obter_permissoes(usuario: Dict[str, Any] = Depends(auth_handler.decode_token)) -> Dict[str, Any]:
    """Devolve matriz de referência e capacidades do usuário revalidadas no banco local."""
    return {"matriz": matriz_inicial(), "usuario": capacidades_do_perfil(str(usuario.get("role", ""))),
            "simulacao_disponivel": ENV in {"development", "test", "testing"} and isinstance(auth_handler.provider, MockAuthProvider)
            and os.getenv("AGHU_PROVIDER_TYPE", "").upper() == "SIMULADO"}
