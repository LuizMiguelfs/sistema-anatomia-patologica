"""Testes offline: nunca consultam o AD real nem alteram o DB instalado."""
import os
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datetime import datetime, timezone

# Configurar ANTES do import de src.main e src.auth.auth.
os.environ["ENV"] = "testing"
os.environ["AD_URL"] = ""
os.environ["AUTH_ALLOW_MOCK"] = "true"
os.environ["MOCK_AUTH_PASSWORD"] = "admin"  # somente fixture de teste
os.environ["SQLITE_DSN"] = ""
os.environ["JWT_SECRET"] = "chave-exclusiva-testes-nunca-usar-em-producao-1234567890"
# Chave AES-256 só de teste (32 bytes em base64).
os.environ["SAP_DATA_KEY"] = "dGVzdGUtYWVzMjU2LXNvbWVudGUtcGFyYS10ZXN0ZXM="
os.environ.pop("SAP_ROLE_GROUP_MAP", None)

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "sap_auth_test.db"
    monkeypatch.setenv("APP_DB_URL", f"sqlite+aiosqlite:///{path}")
    with TestClient(app) as test_client:
        with sqlite3.connect(path) as conn:
            conn.execute(
                "INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, ?, ?)",
                ("admin", "CHEFIA", 1, datetime.now(timezone.utc).isoformat()),
            )
        yield test_client


@pytest.fixture
def login(client):
    response = client.post("/api/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200, response.text
    return response
