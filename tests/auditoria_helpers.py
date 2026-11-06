# tests/auditoria_helpers.py
"""
Utilitários compartilhados pelos testes da trilha de auditoria (Membro 2).
Usam um banco SQLite temporário: o data/app.db real nunca é alterado.

Desde o módulo de autenticação (PR #2), todo token precisa de um perfil válido e o usuário
precisa estar ativo em `authorized_users`: o perfil é lido do banco a cada requisição.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest
from fastapi.testclient import TestClient

from src.auth.auth import auth_handler
from src.helpers.audit_helper import registrar_auditoria
from src.main import app

GRUPO_TI = "GLO-SEC-HCPE-SETISD"


def _autorizar(db_path: Path, username: str, role: str) -> None:
    """Cadastra (ou reativa) um usuário autorizado no banco temporário do teste."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, 1, ?) "
            "ON CONFLICT(username) DO UPDATE SET role = excluded.role, active = 1",
            (username, role, datetime.now(timezone.utc).isoformat()),
        )


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """TestClient com banco da aplicação isolado e o admin cadastrado como CHEFIA."""
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db_path}")
    with TestClient(app) as client:
        _autorizar(db_path, "admin", "CHEFIA")
        yield client, db_path


def _token(db_path: Path, groups: List[str], role: str = "RECEPCAO") -> str:
    """Cadastra um usuário de teste com o perfil informado e devolve um token de acesso."""
    username = f"teste.{role.lower()}"
    _autorizar(db_path, username, role)
    return auth_handler.create_access_token({"username": username, "role": role, "groups": groups})


def _h(token: str) -> Dict[str, str]:
    """Cabeçalho Authorization para o token."""
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> Dict[str, str]:
    """
    Cabeçalho do admin (CHEFIA + grupo de TI, como no mock), já cadastrado pela fixture.
    Gera o token direto em vez de chamar /api/login, para não gravar o evento LOGIN
    na trilha e não interferir nas contagens dos testes.
    """
    token = auth_handler.create_access_token({"username": "admin", "role": "CHEFIA", "groups": [GRUPO_TI, "Users"]})
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
