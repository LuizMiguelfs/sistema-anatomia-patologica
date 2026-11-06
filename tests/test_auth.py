"""RF001/RF002/RNF001: login, persistência de sessão e RBAC SAP."""
import asyncio
import hashlib
import sqlite3

import jwt
import pytest
from fastapi import HTTPException
from src.auth.auth import auth_handler


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _dbpath(client):
    return client.app.state.app_db.engine.url.database


def test_login_mock_success(client):
    response = client.post("/api/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert "Path=/api" in response.headers["set-cookie"]
    assert "Max-Age=" not in response.headers["set-cookie"]


def test_login_mock_invalid_credentials(client):
    response = client.post("/api/login", data={"username": "admin", "password": "incorreta"})
    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_read_users_me_with_token(client, login):
    response = client.get("/api/users/me", headers=_headers(login.json()["access_token"]))
    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role"] == "CHEFIA"


def test_me_without_token_is_401(client):
    assert client.get("/api/users/me").status_code == 401


def test_local_authorization_required(client):
    with sqlite3.connect(_dbpath(client)) as db:
        db.execute("DELETE FROM authorized_users WHERE username='admin'")
    assert client.post("/api/login", data={"username": "admin", "password": "admin"}).status_code == 403


def test_refresh_is_hashed_at_rest_and_rotates_once(client):
    initial = client.post("/api/login", data={"username": "admin", "password": "admin", "remember_me": "true"})
    assert initial.status_code == 200
    raw = client.cookies.get("refresh_token")
    assert raw and len(raw) > 40
    with sqlite3.connect(_dbpath(client)) as db:
        digest = db.execute("SELECT token FROM refresh_tokens").fetchone()[0]
    assert digest == hashlib.sha256(raw.encode()).hexdigest()
    assert digest != raw
    assert "Max-Age=" in initial.headers["set-cookie"]
    renewed = client.post("/api/token/refresh")
    assert renewed.status_code == 200, renewed.text
    assert client.cookies.get("refresh_token") != raw
    replay = client.post("/api/token/refresh", cookies={"refresh_token": raw})
    assert replay.status_code == 401
    # Sem exclusão física: o token consumido continua no banco, marcado em deleted_at.
    with sqlite3.connect(_dbpath(client)) as db:
        linhas = db.execute("SELECT token, deleted_at FROM refresh_tokens ORDER BY id").fetchall()
    assert len(linhas) == 2
    assert linhas[0][0] == digest and linhas[0][1] is not None
    assert linhas[1][1] is None


def test_logout_invalidates_refresh(client, login):
    old = client.cookies.get("refresh_token")
    assert old
    assert client.post("/api/logout").status_code == 200
    assert client.post("/api/token/refresh", cookies={"refresh_token": old}).status_code == 401
    with sqlite3.connect(_dbpath(client)) as db:
        revogado = db.execute("SELECT deleted_at FROM refresh_tokens WHERE token = ?",
                              (hashlib.sha256(old.encode()).hexdigest(),)).fetchone()
    assert revogado is not None and revogado[0] is not None


def test_account_deactivation_takes_effect_immediately(client, login):
    token = login.json()["access_token"]
    with sqlite3.connect(_dbpath(client)) as db:
        db.execute("UPDATE authorized_users SET active=0 WHERE username='admin'")
    assert client.get("/api/users/me", headers=_headers(token)).status_code == 403
    assert client.post("/api/token/refresh").status_code == 403


def test_deactivated_user_refresh_is_revoked_even_after_reactivation(client, login):
    raw = client.cookies.get("refresh_token")
    assert raw
    with sqlite3.connect(_dbpath(client)) as db:
        db.execute("UPDATE authorized_users SET active=0 WHERE username='admin'")
    assert client.post("/api/token/refresh").status_code == 403
    with sqlite3.connect(_dbpath(client)) as db:
        db.execute("UPDATE authorized_users SET active=1 WHERE username='admin'")
    assert client.post("/api/token/refresh", cookies={"refresh_token": raw}).status_code == 401


def test_role_change_takes_effect_immediately(client, login):
    token = login.json()["access_token"]
    with sqlite3.connect(_dbpath(client)) as db:
        db.execute("UPDATE authorized_users SET role='RESIDENTE' WHERE username='admin'")
    assert client.get("/api/users/me", headers=_headers(token)).json()["role"] == "RESIDENTE"


def test_reject_foreign_origin_in_cookie_routes(client, login):
    response = client.post("/api/token/refresh", headers={"Origin": "https://site-invalido.example"})
    assert response.status_code == 403


def test_rejects_invalid_token_type(client, login):
    token = jwt.encode({"sub": "admin", "groups": [], "iat": 1, "exp": 9999999999, "typ": "refresh"},
                       "chave-exclusiva-testes-nunca-usar-em-producao-1234567890", algorithm="HS256")
    assert client.get("/api/users/me", headers=_headers(token)).status_code == 401


def test_rbac_denies_other_roles():
    dependency = auth_handler.require_roles("PRECEPTORIA")
    with pytest.raises(HTTPException) as err:
        asyncio.run(dependency({"username": "admin", "role": "RECEPCAO"}))
    assert err.value.status_code == 403


def test_ad_disabled_prevents_refresh(client, login, monkeypatch):
    monkeypatch.setattr(auth_handler.provider, "search_user", lambda u: {
        "exists": True, "enabled": False, "username": u, "groups": []
    })
    assert client.post("/api/token/refresh").status_code == 401


def test_audit_written_for_login_and_logout(client, login):
    assert client.post("/api/logout").status_code == 200
    with sqlite3.connect(_dbpath(client)) as db:
        events = {row[0] for row in db.execute("SELECT acao FROM audit_logs").fetchall()}
    assert {"LOGIN", "LOGOUT"}.issubset(events)


@pytest.mark.parametrize("role", ["RECEPCAO", "LABORATORIO", "RESIDENTE", "PRECEPTORIA", "CHEFIA"])
def test_all_five_sap_roles_can_be_assigned(client, role):
    with sqlite3.connect(_dbpath(client)) as db:
        db.execute("UPDATE authorized_users SET role=? WHERE username='admin'", (role,))
    signed_in = client.post("/api/login", data={"username": "admin", "password": "admin"})
    assert signed_in.status_code == 200
    user = client.get("/api/users/me", headers=_headers(signed_in.json()["access_token"]))
    assert user.json()["role"] == role


@pytest.mark.parametrize("role", ["RECEPCAO", "LABORATORIO", "RESIDENTE", "PRECEPTORIA", "CHEFIA"])
def test_rbac_guard_per_role(role):
    permitted = auth_handler.require_roles(role)
    assert asyncio.run(permitted({"username": "test", "role": role}))["role"] == role
    forbidden = auth_handler.require_roles("PRECEPTORIA" if role != "PRECEPTORIA" else "CHEFIA")
    with pytest.raises(HTTPException) as error:
        asyncio.run(forbidden({"username": "test", "role": role}))
    assert error.value.status_code == 403
