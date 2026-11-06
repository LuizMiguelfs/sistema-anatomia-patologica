# tests/test_health.py
"""/api/health é público: nunca pode expor detalhes de conexão dos bancos (RNF007)."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient com banco da aplicação isolado."""
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")
    with TestClient(app) as c:
        yield c


def test_health_nao_expoe_detalhes_do_erro(client, monkeypatch):
    """Uma falha de conexão retorna só 'error', sem a mensagem original."""
    segredo = "postgresql://usuario_secreto:senha123@host-interno:5432/aghu"

    class SessaoQuebrada:
        async def __aenter__(self):
            raise RuntimeError(f"falha ao conectar em {segredo}")

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(client.app.state.app_db, "async_session_maker", lambda: SessaoQuebrada())
    r = client.get("/api/health")
    assert r.status_code == 503
    assert r.json()["databases"]["app_db"] == "error"
    assert "senha123" not in r.text and "usuario_secreto" not in r.text
