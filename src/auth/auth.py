"""Autenticação SAP: AD/LDAP (identidade), autorização local (perfil) e sessão.

Refresh usa busca de conta via AD com usuário de serviço, NUNCA bind sem senha.
Sem autorização local ativa ou conta AD válida não se emite sessão.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
import re
import secrets
import ssl
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from ldap3 import ALL, SUBTREE, SIMPLE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPBindError, LDAPException
from ldap3.utils.conv import escape_filter_chars
from ldap3.utils.dn import parse_dn
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings  # valida configurações na inicialização
from ..helpers.audit_helper import registrar_auditoria
from ..models.authorized_user import AuthorizedUser
from ..models.refresh_token import RefreshToken
from ..resources.database import get_app_db_session

load_dotenv()
log = logging.getLogger(__name__)
ENV = os.getenv("ENV", "development").lower()
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", "24"))  # legado; preferir ACCESS_TOKEN_MINUTES
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_TOKEN_EXP_DAYS = int(os.getenv("REFRESH_TOKEN_EXP_DAYS", "30"))
SESSION_REFRESH_HOURS = int(os.getenv("SESSION_REFRESH_HOURS", "12"))
COOKIE_SECURE = ENV == "production" or os.getenv("REFRESH_COOKIE_SECURE", "false").lower() == "true"
ROLES = frozenset({"RECEPCAO", "LABORATORIO", "RESIDENTE", "PRECEPTORIA", "CHEFIA"})
ADMIN_GROUP = "GLO-SEC-HCPE-SETISD"  # Administração do framework, NÃO sinônimo de Chefia SAP.
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def now_utc() -> datetime:
    """Agora em UTC, sem fuso (formato gravado no SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_username(value: str) -> str:
    """Normaliza o login de rede (sem domínio, minúsculo); 401 se inválido ou de outro domínio."""
    if not isinstance(value, str):
        raise HTTPException(401, "Credenciais inválidas")
    user = value.strip()
    domain = os.getenv("AD_DOMAIN", "EBSERHNET")
    if "\\" in user:
        supplied_domain, user = user.split("\\", 1)
        if supplied_domain.casefold() != domain.casefold():
            raise HTTPException(401, "Credenciais inválidas")
    if not USERNAME_PATTERN.fullmatch(user):
        raise HTTPException(401, "Credenciais inválidas")
    return user.lower()


def _hash_token(value: str) -> str:
    """SHA-256 do refresh token: o valor cru nunca é gravado."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_groups(value: Any) -> list[str]:
    """Lista de grupos limpa: só textos curtos, sem repetição, no máximo 200."""
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(item for item in value if isinstance(item, str) and len(item) <= 256))[:200]


def _ldap_group_name(dn: str) -> str | None:
    """Extrai o CN de um DN de grupo do AD; None se não houver."""
    try:
        for attribute, value, _separator in parse_dn(str(dn)):
            if attribute.upper() == "CN":
                return value
    except (ValueError, TypeError, LDAPException):
        return None
    return None


def _role_group_policy() -> dict[str, set[str]]:
    """Se fornecido, restringe o perfil local a grupos AD autorizados pela instituição."""
    raw = os.getenv("SAP_ROLE_GROUP_MAP", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict) or not all(
            role in ROLES and isinstance(groups, list) and groups
            and all(isinstance(g, str) and g.strip() for g in groups)
            for role, groups in parsed.items()
        ):
            raise ValueError("Mapa de grupos inválido")
        if parsed and set(parsed) != ROLES:
            raise ValueError("Mapa deve conter os cinco perfis, sem omissões")
        return {role: {g.casefold() for g in groups} for role, groups in parsed.items()}
    except (ValueError, TypeError) as exc:
        raise RuntimeError("SAP_ROLE_GROUP_MAP deve ser JSON {PERFIL: [GRUPO_AD]}") from exc


def grupos_permitem_perfil(role: str, groups: list[str]) -> bool:
    """True se os grupos do AD atendem ao SAP_ROLE_GROUP_MAP para o perfil (sem mapa: sempre True)."""
    exigidos = _role_group_policy().get(role)
    return not exigidos or bool(exigidos.intersection(g.casefold() for g in groups))


class AuthProviderInterface(ABC):
    @abstractmethod
    def authenticate_user(self, username: str, password: str) -> dict:
        """Valida login e senha na fonte de identidade e devolve o perfil profissional."""

    @abstractmethod
    def search_user(self, username: str) -> dict:
        """Consulta a conta pelo login (existência, situação, nome, setor e grupos)."""


class MockAuthProvider(AuthProviderInterface):
    """Somente desenvolvimento/testes; jamais disponibilizado em produção."""
    _users = {
        "admin": ("Administrador do Sistema", "admin@ebserh.gov.br", "SETISD / HC-UFPE"),
        "joao.silva": ("João da Silva", "joao.silva@ebserh.gov.br", "UTI Adulto / HC-UFPE"),
        "maria.souza": ("Maria Souza", "maria.souza@ebserh.gov.br", "Bloco Cirúrgico / HC-UFPE"),
    }

    def search_user(self, username: str) -> dict:
        """Consulta um login no catálogo simulado (só desenvolvimento/testes)."""
        username = normalize_username(username)
        info = self._users.get(username)
        if not info and "." in username:
            info = (" ".join(x.capitalize() for x in username.split(".")),
                    f"{username}@ebserh.gov.br", "Unidade Hospitalar / HC-UFPE")
        return {
            "exists": bool(info), "enabled": bool(info), "username": username,
            "displayName": info[0] if info else "", "email": info[1] if info else "",
            "department": info[2] if info else "", "title": "",
            "groups": [ADMIN_GROUP, "Users"] if username == "admin" else [],
        }

    def authenticate_user(self, username: str, password: str) -> dict:
        """Login simulado: só o admin, com a senha de MOCK_AUTH_PASSWORD."""
        username = normalize_username(username)
        expected = os.getenv("MOCK_AUTH_PASSWORD", "")
        if not expected:
            raise HTTPException(503, "Mock exige MOCK_AUTH_PASSWORD definido no ambiente")
        if username != "admin" or not secrets.compare_digest(password or "", expected):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
        info = self.search_user(username)
        return _as_profile(info)


def _as_profile(info: dict) -> dict:
    """Formato do perfil profissional usado no token (listas, como no AD)."""
    return {
        "username": info["username"], "groups": _safe_groups(info.get("groups", [])),
        "displayName": [info.get("displayName", "")],
        "email": [info.get("email", "")],
        "department": [info.get("department", "")],
        "title": [info.get("title", "")],
    }


class ActiveDirectoryAuthProvider(AuthProviderInterface):
    def __init__(self) -> None:
        """Valida a configuração do AD (só LDAPS, sem credencial na URL) e prepara o servidor."""
        ad_url = os.getenv("AD_URL", "")
        self.base_dn = os.getenv("AD_BASEDN", "")
        self.bind_user = os.getenv("AD_BIND_USER", "")
        self.bind_password = os.getenv("AD_BIND_PASSWORD", "")
        self.domain = os.getenv("AD_DOMAIN", "EBSERHNET")
        parsed = urlparse(ad_url)
        if parsed.username or parsed.password:
            raise RuntimeError("Credenciais não devem aparecer em AD_URL")
        if parsed.scheme not in {"ldap", "ldaps"} or not parsed.hostname or not self.base_dn:
            raise RuntimeError("AD_URL e AD_BASEDN inválidos")
        if parsed.scheme != "ldaps":
            raise RuntimeError("AD_URL deve usar LDAPS; binds em LDAP sem TLS foram bloqueados")
        tls = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=os.getenv("AD_CA_CERT") or None)
        self.server = Server(parsed.hostname, port=parsed.port or 636,
                             use_ssl=True, tls=tls, get_info=ALL, connect_timeout=5)

    def _read_entry(self, conn: Connection, username: str) -> dict:
        """Lê a conta no AD pelo sAMAccountName e devolve situação, dados profissionais e grupos."""
        attributes = ["displayName", "mail", "department", "title", "memberOf", "userAccountControl"]
        query = f"(&(objectClass=user)(sAMAccountName={escape_filter_chars(username)}))"
        conn.search(self.base_dn, query, search_scope=SUBTREE, attributes=attributes, size_limit=2)
        if len(conn.entries) != 1:
            return {"exists": False, "enabled": False, "username": username,
                    "displayName": "", "email": "", "department": "", "groups": []}
        attributes = conn.entries[0].entry_attributes_as_dict

        def value(name: str, default: Any = "") -> Any:
            """Primeiro valor de um atributo do AD, ou o padrão."""
            item = attributes.get(name, default)
            return item[0] if isinstance(item, (list, tuple)) and item else (item or default)

        group_dns = attributes.get("memberOf", []) or []
        if not isinstance(group_dns, list):
            group_dns = [group_dns]
        groups = [name for dn in group_dns if (name := _ldap_group_name(str(dn)))]
        try:
            flags = int(value("userAccountControl", 2))
        except (TypeError, ValueError):
            flags = 2
        return {
            "exists": True, "enabled": not bool(flags & 2), "username": username,
            "displayName": str(value("displayName", username)), "email": str(value("mail")),
            "department": str(value("department")), "title": str(value("title")),
            "groups": groups,
        }

    def authenticate_user(self, username: str, password: str) -> dict:
        """Autentica com bind do próprio usuário no AD e devolve o perfil profissional."""
        username = normalize_username(username)
        if not password:
            raise HTTPException(401, "Credenciais inválidas")
        user_conn = None
        service_conn = None
        try:
            user_conn = Connection(self.server, user=f"{self.domain}\\{username}", password=password,
                                   authentication=SIMPLE, auto_bind=True, raise_exceptions=True)
            search_conn = user_conn
            if self.bind_user and self.bind_password:
                service_conn = Connection(self.server, user=self.bind_user,
                                          password=self.bind_password, authentication=SIMPLE,
                                          auto_bind=True, raise_exceptions=True)
                search_conn = service_conn
            info = self._read_entry(search_conn, username)
            if not info["exists"] or not info["enabled"]:
                raise HTTPException(401, "Credenciais inválidas")
            return _as_profile(info)
        except LDAPBindError:
            raise HTTPException(401, "Credenciais inválidas") from None
        except LDAPException:
            log.warning("Falha de comunicação ao autenticar no AD")
            raise HTTPException(503, "Autenticação corporativa indisponível") from None
        finally:
            if service_conn:
                service_conn.unbind()
            if user_conn:
                user_conn.unbind()

    def search_user(self, username: str) -> dict:
        """Consulta a conta no AD com a conta de serviço (sem senha do usuário)."""
        username = normalize_username(username)
        if not (self.bind_user and self.bind_password):
            raise HTTPException(503, "Conta de serviço AD necessária para consulta/renovação")
        conn = None
        try:
            conn = Connection(self.server, user=self.bind_user, password=self.bind_password,
                              authentication=SIMPLE, auto_bind=True, raise_exceptions=True)
            return self._read_entry(conn, username)
        except LDAPException:
            log.warning("Falha ao consultar conta no AD")
            raise HTTPException(503, "Consulta corporativa indisponível") from None
        finally:
            if conn:
                conn.unbind()


class AuthHandler:
    def __init__(self) -> None:
        """Valida a configuração de sessão e escolhe o provedor de identidade (AD ou Mock em dev)."""
        if ACCESS_TOKEN_MINUTES < 1 or REFRESH_TOKEN_EXP_DAYS < 1 or SESSION_REFRESH_HOURS < 1:
            raise RuntimeError("Durações de sessão inválidas")
        if len(JWT_SECRET) < 32:
            raise RuntimeError("JWT_SECRET com pelo menos 32 caracteres é obrigatório")
        if ENV == "production":
            if not JWT_SECRET or len(JWT_SECRET) < 32 or JWT_SECRET in {
                "super-secret-key-change-in-production", "SUA_CHAVE_SECRETA_SUPER_FORTE_AQUI_ALTERAR_EM_PRODUCAO"
            }:
                raise RuntimeError("JWT_SECRET seguro é obrigatório em produção")
            if not os.getenv("AD_URL"):
                raise RuntimeError("AD_URL é obrigatório em produção (Mock proibido)")
            if not (os.getenv("AD_BIND_USER") and os.getenv("AD_BIND_PASSWORD")):
                raise RuntimeError("Conta de serviço AD obrigatória em produção para revalidação")
        _role_group_policy()  # valida JSON durante startup
        if os.getenv("AD_URL"):
            self.provider: AuthProviderInterface = ActiveDirectoryAuthProvider()
        elif ENV in {"development", "test", "testing"} and os.getenv("AUTH_ALLOW_MOCK", "").lower() == "true":
            self.provider = MockAuthProvider()
        else:
            raise RuntimeError("Mock exige AUTH_ALLOW_MOCK=true e ambiente não produtivo")
        if isinstance(self.provider, MockAuthProvider):
            log.warning("Autenticação Mock ativada exclusivamente para desenvolvimento")

    def authenticate_user(self, username: str, password: str) -> dict:
        """Autentica no provedor configurado."""
        return self.provider.authenticate_user(username, password)

    def search_ad_user(self, username: str) -> dict:
        """Consulta um login no provedor configurado."""
        return self.provider.search_user(username)

    async def authorize_user(self, username: str, groups: list[str], db: AsyncSession) -> AuthorizedUser:
        """Exige usuário ativo em authorized_users, com perfil válido e grupos do AD exigidos; 403 caso contrário."""
        username = normalize_username(username)
        result = await db.execute(select(AuthorizedUser).where(AuthorizedUser.username == username))
        local_user = result.scalar_one_or_none()
        if not local_user or not local_user.active or local_user.role not in ROLES:
            raise HTTPException(403, "Usuário não autorizado para o SAP")
        if not grupos_permitem_perfil(local_user.role, groups):
            raise HTTPException(403, "Perfil sem grupo corporativo necessário")
        return local_user

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        """Emite o JWT de acesso (curto) com login, perfil, grupos e dados profissionais do próprio usuário."""
        username = normalize_username(data.get("username", data.get("sub", "")))
        role = data.get("role")
        if role not in ROLES:
            raise ValueError("Perfil inválido para JWT")
        now = datetime.now(timezone.utc)
        claims = {"sub": username, "username": username, "role": role,
                  "groups": _safe_groups(data.get("groups", [])), "typ": "access",
                  "iat": int(now.timestamp()),
                  "exp": int((now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_MINUTES))).timestamp())}
        # Apenas dados profissionais mínimos do PRÓPRIO usuário, sem dados clínicos.
        for key in ("displayName", "department", "title", "email"):
            item = data.get(key, "")
            value = item[0] if isinstance(item, list) and item else item
            claims[key] = [str(value)[:256]] if isinstance(value, str) and value else []
        if not JWT_SECRET:
            raise RuntimeError("JWT_SECRET precisa estar configurado")
        return jwt.encode(claims, JWT_SECRET, algorithm="HS256")

    async def create_refresh_token(self, user_id: str, groups: list, db: AsyncSession,
                                   remember_me: bool = False, ip: str | None = None) -> str:
        """Cria token e registra evento de segurança na mesma transação."""
        raw = secrets.token_urlsafe(48)
        ttl = timedelta(days=REFRESH_TOKEN_EXP_DAYS) if remember_me else timedelta(hours=SESSION_REFRESH_HOURS)
        db.add(RefreshToken(user_id=normalize_username(user_id), token=_hash_token(raw),
                            groups={"remember_me": bool(remember_me)}, expires_at=now_utc() + ttl))
        try:
            await registrar_auditoria(db, usuario=user_id, categoria="SEGURANCA", acao="LOGIN",
                                      recurso="sessao", dados_novos={"sessao": "criada"},
                                      ip_origem=ip, commit=False)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return raw

    async def verify_refresh_token(self, raw: str, db: AsyncSession) -> RefreshToken:
        """Busca o refresh token ativo (não revogado e não expirado); 401 caso contrário."""
        if not raw or len(raw) > 512:
            raise HTTPException(401, "Sessão expirada ou inválida")
        result = await db.execute(select(RefreshToken).where(RefreshToken.token == _hash_token(raw),
                                                             RefreshToken.deleted_at.is_(None)))
        token = result.scalar_one_or_none()
        if not token or token.expires_at <= now_utc():
            raise HTTPException(401, "Sessão expirada ou inválida")
        return token

    async def rotate_refresh_token(self, raw: str, db: AsyncSession, username: str,
                                   remember_me: bool, ip: str | None = None) -> str:
        """Apenas uma requisição concorrente consome cada refresh token (exclusão lógica)."""
        raw_new = secrets.token_urlsafe(48)
        consumed = await db.execute(
            update(RefreshToken).where(RefreshToken.token == _hash_token(raw),
                                       RefreshToken.user_id == username,
                                       RefreshToken.expires_at > now_utc(),
                                       RefreshToken.deleted_at.is_(None))
            .values(deleted_at=now_utc())
            .returning(RefreshToken.user_id)
        )
        if consumed.scalar_one_or_none() is None:
            await db.rollback()
            raise HTTPException(401, "Sessão já utilizada ou expirada")
        ttl = timedelta(days=REFRESH_TOKEN_EXP_DAYS) if remember_me else timedelta(hours=SESSION_REFRESH_HOURS)
        db.add(RefreshToken(user_id=username, token=_hash_token(raw_new),
                            groups={"remember_me": remember_me}, expires_at=now_utc() + ttl))
        try:
            await registrar_auditoria(db, usuario=username, categoria="SEGURANCA", acao="RENOVAR_SESSAO",
                                      recurso="sessao", dados_anteriores={"sessao": "anterior"},
                                      dados_novos={"sessao": "renovada"}, ip_origem=ip, commit=False)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return raw_new

    async def invalidate_refresh_token(self, raw: str, db: AsyncSession, ip: str | None = None) -> None:
        """Revoga o refresh token (exclusão lógica) e audita o logout na mesma transação."""
        if not raw or len(raw) > 512:
            return
        result = await db.execute(
            update(RefreshToken).where(RefreshToken.token == _hash_token(raw),
                                       RefreshToken.deleted_at.is_(None))
            .values(deleted_at=now_utc())
            .returning(RefreshToken.user_id)
        )
        user_id = result.scalar_one_or_none()
        if user_id:
            try:
                await registrar_auditoria(db, usuario=user_id, categoria="SEGURANCA", acao="LOGOUT",
                                          recurso="sessao", dados_anteriores={"sessao": "ativa"},
                                          dados_novos={"sessao": "revogada"}, ip_origem=ip, commit=False)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def decode_token(self, token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_app_db_session)) -> dict:
        """Valida o JWT e relê o perfil no banco a cada requisição (revogação imediata)."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"],
                                 options={"require": ["exp", "iat", "sub", "typ"]})
            if payload.get("typ") != "access" or not isinstance(payload.get("groups"), list):
                raise jwt.InvalidTokenError()
            username = normalize_username(payload["sub"])
        except (jwt.InvalidTokenError, HTTPException):
            raise HTTPException(401, "Sessão inválida ou expirada") from None
        local_user = await self.authorize_user(username, payload["groups"], db)
        # Papéis revogados/alterados no banco têm efeito imediato, sem aguardar expiração do JWT.
        return {"username": username, "role": local_user.role, "groups": payload["groups"],
                "displayName": payload.get("displayName") or [username],
                "department": payload.get("department", []),
                "email": payload.get("email", []),
                "title": payload.get("title", [])}

    def require_roles(self, *roles: str) -> Callable[..., Awaitable[dict]]:
        """Usar como Depends(auth_handler.require_roles('RECEPCAO', ...)) em rotas SAP."""
        if not roles or any(role not in ROLES for role in roles):
            raise ValueError("Lista de perfis RBAC inválida")

        async def dependency(current_user: dict = Depends(self.decode_token)) -> dict:
            """Libera a rota só para os perfis informados; 403 caso contrário."""
            if current_user.get("role") not in roles:
                raise HTTPException(403, "Sem permissão para esta operação")
            return current_user

        return dependency


auth_handler = AuthHandler()
