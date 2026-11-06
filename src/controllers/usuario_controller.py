"""
Controller da gestão de usuários do SAP (RF028 / UC026).

Regras (decididas com o grupo):
* Só a Chefia gerencia usuários (a checagem de perfil fica no router).
* Ninguém altera o próprio perfil nem inativa a si mesmo.
* O login precisa existir e estar ativo no AD; o nome vem do AD, não do formulário.
* Não existe exclusão: inativar mantém o registro (SPEC.md, sem exclusão física).
* Toda alteração grava auditoria SEGURANCA na mesma transação (RN-04).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from ..auth.auth import grupos_permitem_perfil, normalize_username
from ..helpers.audit_helper import registrar_auditoria
from ..providers.interfaces.usuario_provider_interface import UsuarioProviderInterface

logger = logging.getLogger("usuarios")

CATEGORIA_AUDITORIA = "SEGURANCA"

BuscaAD = Callable[[str], Dict[str, Any]]


def _recurso(username: str) -> str:
    """Recurso auditado de um usuário (ex.: usuario:joao.silva)."""
    return f"usuario:{username}"


def _sem_auto_alteracao(ator: str, username: str, mensagem: str) -> None:
    """Impede que a pessoa altere o próprio acesso."""
    if normalize_username(ator) == username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=mensagem)


async def _consultar_ad(buscar_no_ad: BuscaAD, username: str) -> Dict[str, Any]:
    """Consulta o login no AD; 404 se não existir ou estiver desativado."""
    info = await run_in_threadpool(buscar_no_ad, username)
    if not info.get("exists") or not info.get("enabled"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Login não encontrado ou desativado no Active Directory.")
    return info


def _exigir_grupos(perfil: str, info: Dict[str, Any]) -> None:
    """Respeita o SAP_ROLE_GROUP_MAP, quando configurado pela instituição."""
    if not grupos_permitem_perfil(perfil, info.get("groups", [])):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="O usuário não pertence ao grupo do AD exigido para este perfil.")


async def _usuario_ou_404(provider: UsuarioProviderInterface, username: str) -> Dict[str, Any]:
    """Busca o usuário autorizado ou responde 404."""
    usuario = await provider.buscar(username)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não cadastrado no SAP.")
    return usuario


async def _gravar(
    provider: UsuarioProviderInterface,
    acao: str,
    alteracao: Callable[[], Any],
    ator: str,
    username: str,
    antes: Optional[Dict[str, Any]],
    depois: Dict[str, Any],
    ip: Optional[str],
) -> None:
    """Executa a alteração e a auditoria na mesma transação; desfaz tudo em caso de erro."""
    try:
        await alteracao()
        await registrar_auditoria(provider.session, usuario=ator, categoria=CATEGORIA_AUDITORIA, acao=acao,
                                  recurso=_recurso(username), dados_anteriores=antes, dados_novos=depois,
                                  ip_origem=ip, commit=False)
        await provider.commit()
    except IntegrityError:
        await provider.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já cadastrado no SAP.") from None
    except Exception as erro:
        await provider.rollback()
        # Padrão de log de erro: ação + tipo da exceção, sem dados do registro (RNF007).
        logger.error("Falha em %s: %s", acao, erro.__class__.__name__)
        raise


async def listar_usuarios(provider: UsuarioProviderInterface) -> List[Dict[str, Any]]:
    """Lista os usuários autorizados (ativos e inativos)."""
    return await provider.listar()


async def incluir_usuario(
    provider: UsuarioProviderInterface,
    buscar_no_ad: BuscaAD,
    ator: str,
    username: str,
    perfil: str,
    ip: Optional[str],
) -> Dict[str, Any]:
    """Autoriza um login do AD no SAP com o perfil escolhido."""
    username = normalize_username(username)
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o login de rede.")
    if await provider.buscar(username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Usuário já cadastrado no SAP. Altere o perfil ou reative o acesso.")
    info = await _consultar_ad(buscar_no_ad, username)
    _exigir_grupos(perfil, info)
    nome = (info.get("displayName") or "").strip() or None
    agora = datetime.now(timezone.utc)
    await _gravar(provider, "INCLUIR_USUARIO", lambda: provider.inserir(username, nome, perfil, agora),
                  ator, username, None, {"nome": nome, "perfil": perfil, "ativo": True}, ip)
    return await _usuario_ou_404(provider, username)


async def alterar_perfil(
    provider: UsuarioProviderInterface,
    buscar_no_ad: BuscaAD,
    ator: str,
    username: str,
    perfil: str,
    ip: Optional[str],
) -> Dict[str, Any]:
    """Troca o perfil de um usuário (não vale para o próprio usuário)."""
    username = normalize_username(username)
    _sem_auto_alteracao(ator, username, "Você não pode alterar o próprio perfil.")
    atual = await _usuario_ou_404(provider, username)
    if atual["perfil"] == perfil:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O usuário já tem esse perfil.")
    _exigir_grupos(perfil, await _consultar_ad(buscar_no_ad, username))
    agora = datetime.now(timezone.utc)
    await _gravar(provider, "ALTERAR_PERFIL_USUARIO",
                  lambda: provider.atualizar(username, perfil, atual["ativo"], agora),
                  ator, username, {"perfil": atual["perfil"]}, {"perfil": perfil}, ip)
    return await _usuario_ou_404(provider, username)


async def alterar_situacao(
    provider: UsuarioProviderInterface,
    ator: str,
    username: str,
    ativo: bool,
    ip: Optional[str],
) -> Dict[str, Any]:
    """Inativa ou reativa o acesso (não vale para o próprio usuário). Efeito imediato nas sessões."""
    username = normalize_username(username)
    _sem_auto_alteracao(ator, username, "Você não pode alterar a situação do próprio acesso.")
    atual = await _usuario_ou_404(provider, username)
    if atual["ativo"] == ativo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="O usuário já está ativo." if ativo else "O usuário já está inativo.")
    agora = datetime.now(timezone.utc)
    await _gravar(provider, "REATIVAR_USUARIO" if ativo else "INATIVAR_USUARIO",
                  lambda: provider.atualizar(username, atual["perfil"], ativo, agora),
                  ator, username, {"ativo": atual["ativo"]}, {"ativo": ativo}, ip)
    return await _usuario_ou_404(provider, username)
