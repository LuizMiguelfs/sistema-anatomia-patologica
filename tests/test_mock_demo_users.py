"""Login simulado com usuários de demonstração (MOCK_AUTH_USERS), só fora de produção."""
import sqlite3
from datetime import datetime, timezone


def test_usuario_demo_so_entra_se_listado_e_autorizado(client, monkeypatch, tmp_path):
    db = tmp_path / "sap_auth_test.db"
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, 1, ?)",
                     ("demo.residente", "RESIDENTE", datetime.now(timezone.utc).isoformat()))

    monkeypatch.delenv("MOCK_AUTH_USERS", raising=False)
    assert client.post("/api/login", data={"username": "demo.residente", "password": "admin"}).status_code == 401

    monkeypatch.setenv("MOCK_AUTH_USERS", "demo.residente, demo.recepcao")
    r = client.post("/api/login", data={"username": "demo.residente", "password": "admin"})
    assert r.status_code == 200, r.text
    assert client.post("/api/login", data={"username": "demo.residente", "password": "errada"}).status_code == 401
    # Listado mas sem cadastro local ativo: continua sem acesso (autorização local).
    assert client.post("/api/login", data={"username": "demo.recepcao", "password": "admin"}).status_code in (401, 403)
