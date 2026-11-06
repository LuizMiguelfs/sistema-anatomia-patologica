"""Endpoints públicos de sessão e endpoint autenticado de perfil.

Cookie HttpOnly restrito a /api; access token fica somente em memória no frontend.
"""
import os
from typing import Any, Dict
from datetime import timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ..auth.auth import (
    ACCESS_TOKEN_MINUTES, COOKIE_SECURE, ENV, REFRESH_TOKEN_EXP_DAYS,
    auth_handler,
)
from ..resources.database import get_app_db_session

router = APIRouter(prefix="/api", tags=["Authentication"])
COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api"


def _cookie(response: Response, token: str, remember_me: bool) -> None:
    """Sem 'lembrar': cookie de sessão, expira quando o navegador encerra."""
    kwargs = {"key": COOKIE_NAME, "value": token, "httponly": True,
              "secure": COOKIE_SECURE, "samesite": "lax", "path": COOKIE_PATH}
    if remember_me:
        kwargs["max_age"] = REFRESH_TOKEN_EXP_DAYS * 86400
    response.set_cookie(**kwargs)


def _clear_cookie(response: Response) -> None:
    """Remove o cookie de refresh com os mesmos atributos usados na criação."""
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH, httponly=True,
                           secure=COOKIE_SECURE, samesite="lax")


def _validate_origin(request: Request) -> None:
    """Verificação complementar à proteção SameSite contra CSRF nas rotas de cookie."""
    origin = request.headers.get("origin")
    if not origin:
        return  # Clientes de API sem Origin, não autenticados por cookie no navegador.
    allowed = {s.strip().rstrip("/") for s in os.getenv("ALLOWED_ORIGINS", "").split(",") if s.strip()}
    # Host é usado apenas em desenvolvimento; em produção usar a lista explícita.
    if ENV != "production":
        allowed.add(f"{request.url.scheme}://{request.url.netloc}")
        allowed.update({"http://localhost:5173", "http://127.0.0.1:5173"})
    if origin.rstrip("/") not in allowed:
        raise HTTPException(403, "Origem não autorizada")


def _ip(request: Request) -> str | None:
    # Não confiar em X-Forwarded-For sem validação de proxy de confiança.
    """IP de origem para a auditoria (sem confiar em X-Forwarded-For)."""
    return request.client.host if request.client else None


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Form(False),
    db: AsyncSession = Depends(get_app_db_session),
) -> Dict[str, Any]:
    """Autentica no AD, exige autorização local e devolve o access token; o refresh vai em cookie HttpOnly."""
    _validate_origin(request)
    try:
        user = await run_in_threadpool(auth_handler.authenticate_user,
                                       form_data.username, form_data.password)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Serviço de autenticação indisponível") from None

    authorized = await auth_handler.authorize_user(user["username"], user.get("groups", []), db)
    token = auth_handler.create_access_token({**user, "role": authorized.role})
    refresh = await auth_handler.create_refresh_token(user_id=user["username"],
                                                      groups=user.get("groups", []),
                                                      remember_me=remember_me,
                                                      db=db, ip=_ip(request))
    _cookie(response, refresh, remember_me)
    return {"access_token": token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_MINUTES * 60}


@router.post("/token/refresh")
async def refresh_token(request: Request, response: Response,
                        db: AsyncSession = Depends(get_app_db_session)) -> Dict[str, Any]:
    """Renova a sessão: revalida a conta no AD e o perfil local, consome o refresh (uso único) e emite novos tokens."""
    _validate_origin(request)
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(401, "Sessão não encontrada")
    token_db = await auth_handler.verify_refresh_token(raw, db)
    username = token_db.user_id
    remember_me = bool((token_db.groups or {}).get("remember_me", False)) if isinstance(token_db.groups, dict) else False

    # Revalidação real com busca AD de conta ativa; não repete bind com senha None.
    identity = await run_in_threadpool(auth_handler.search_ad_user, username)
    if not identity.get("exists") or not identity.get("enabled"):
        await auth_handler.invalidate_refresh_token(raw, db, ip=_ip(request))
        _clear_cookie(response)
        raise HTTPException(401, "Conta não disponível para renovação")
    try:
        authorized = await auth_handler.authorize_user(username, identity.get("groups", []), db)
    except HTTPException as exc:
        # Usuário/perfil removido: revoga a sessão antiga para impedir reutilização
        # caso a autorização seja concedida novamente no futuro.
        if exc.status_code == 403:
            await auth_handler.invalidate_refresh_token(raw, db, ip=_ip(request))
            _clear_cookie(response)
        raise
    new_refresh = await auth_handler.rotate_refresh_token(raw, db, username, remember_me, ip=_ip(request))
    new_access = auth_handler.create_access_token({
        **identity, "username": username, "role": authorized.role,
        "groups": identity.get("groups", []),
    }, expires_delta=timedelta(minutes=ACCESS_TOKEN_MINUTES))
    _cookie(response, new_refresh, remember_me)
    return {"access_token": new_access, "token_type": "bearer", "expires_in": ACCESS_TOKEN_MINUTES * 60}


@router.post("/logout")
async def logout(request: Request, response: Response,
                 db: AsyncSession = Depends(get_app_db_session)) -> Dict[str, str]:
    """Encerra a sessão: revoga o refresh token (exclusão lógica) e apaga o cookie."""
    _validate_origin(request)
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        await auth_handler.invalidate_refresh_token(raw, db, ip=_ip(request))
    _clear_cookie(response)
    return {"message": "Sessão encerrada"}


@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(auth_handler.decode_token)) -> dict:
    """Dados do usuário logado (perfil lido do banco nesta requisição)."""
    return current_user
