# tests/auditoria_helpers.py
"""
Utilitários compartilhados pelos testes da trilha de auditoria (Membro 2).
Usam um banco SQLite temporário: o data/app.db real nunca é alterado.
"""

from typing import Any, Callable, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from src.auth.auth import auth_handler
from src.helpers.audit_helper import registrar_auditoria
from src.main import app


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """TestClient com banco da aplicação isolado e token de administrador (grupo TI)."""
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db_path}")
    with TestClient(app) as client:
        yield client, db_path


def _token(groups: List[str], role: Optional[str] = None) -> str:
    """Gera um token de acesso de teste com os grupos (e o perfil) informados."""
    dados: Dict[str, Any] = {"username": "teste.usuario", "groups": groups}
    if role:
        dados["role"] = role
    return auth_handler.create_access_token(dados)


def _h(token: str) -> Dict[str, str]:
    """Cabeçalho Authorization para o token."""
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> Dict[str, str]:
    """Faz login como admin (grupo de TI no mock) e devolve o cabeçalho."""
    token = client.post("/api/login", data={"username": "admin", "password": "admin"}).json()["access_token"]
    return _h(token)


def _gravar(client: TestClient, **campos: Any) -> int:
    """Grava um evento pelo helper oficial, usando o banco da aplicação do TestClient."""
    async def _executar() -> int:
        async with client.app.state.app_db.async_session_maker() as session:
            dados = {
                "usuario": "joao.silva", "categoria": "NEGOCIO_CLINICO", "acao": "CRIAR_PACIENTE",
                "recurso": "paciente:1", "dados_anteriores": None, "dados_novos": {"nome": "MARIA"},
                "ip_origem": "10.0.0.1",
            }
            dados.update(campos)
            log = await registrar_auditoria(db=session, **dados)
            return log.id
    return client.portal.call(_executar)


def _com_sessao(client: TestClient, funcao: Callable) -> Any:
    """Executa `funcao(session)` numa sessão do banco da aplicação do TestClient."""
    async def _executar() -> Any:
        async with client.app.state.app_db.async_session_maker() as session:
            return await funcao(session)
    return client.portal.call(_executar)
