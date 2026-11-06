# tests/test_usuarios.py
"""Gestão de usuários (RF028 / UC026): só a Chefia, sem auto-alteração, sem exclusão, auditada."""

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from src.auth.auth import auth_handler
from src.controllers import usuario_controller
from src.helpers.crypto_helper import decifrar

GRUPO_TI = "GLO-SEC-HCPE-SETISD"
URL = "/api/admin/usuarios"


def _db(client) -> str:
    """Caminho do banco temporário da fixture `client`."""
    return client.app.state.app_db.engine.url.database


def _autorizar(client, username: str, role: str, ativo: bool = True) -> None:
    """Cadastra um usuário direto no banco temporário (preparação do teste)."""
    with sqlite3.connect(_db(client)) as conn:
        conn.execute("INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, ?, ?)",
                     (username, role, 1 if ativo else 0, datetime.now(timezone.utc).isoformat()))


def _h(username: str, role: str, groups=None) -> dict:
    """Cabeçalho com token de acesso para o usuário informado."""
    token = auth_handler.create_access_token({"username": username, "role": role, "groups": groups or ["Users"]})
    return {"Authorization": f"Bearer {token}"}


def _chefia() -> dict:
    """Admin cadastrado pela fixture como CHEFIA (sem grupo de TI)."""
    return _h("admin", "CHEFIA")


def _auditoria(client) -> list:
    """Eventos de gestão de usuários gravados na trilha."""
    with sqlite3.connect(_db(client)) as conn:
        linhas = conn.execute(
            "SELECT usuario, categoria, acao, recurso, dados_anteriores, dados_novos, ip_origem "
            "FROM audit_logs WHERE recurso LIKE 'usuario:%' ORDER BY id").fetchall()
    return [(u, c, a, r, json.loads(decifrar(ant)) if ant else None, json.loads(decifrar(nov)), ip)
            for u, c, a, r, ant, nov, ip in linhas]


# ------------------------------------------------------------------ acesso
def test_exige_autenticacao(client):
    assert client.get(URL).status_code == 401


def test_so_a_chefia_gerencia_usuarios(client):
    _autorizar(client, "tecnico.ti", "LABORATORIO")
    # Grupo de TI não basta: gestão de usuários é decisão de negócio (Chefia).
    assert client.get(URL, headers=_h("tecnico.ti", "LABORATORIO", [GRUPO_TI])).status_code == 403
    assert client.post(URL, json={"username": "joao.silva", "perfil": "RECEPCAO"},
                       headers=_h("tecnico.ti", "LABORATORIO", [GRUPO_TI])).status_code == 403
    assert client.get(URL, headers=_chefia()).status_code == 200


def test_nao_existe_rota_de_exclusao(client):
    _autorizar(client, "joao.silva", "RECEPCAO")
    assert client.delete(f"{URL}/joao.silva", headers=_chefia()).status_code in (404, 405)


# ------------------------------------------------------------------ inclusão
def test_inclui_usuario_com_nome_do_ad_e_auditoria(client):
    r = client.post(URL, json={"username": "Joao.Silva", "perfil": "RECEPCAO"}, headers=_chefia())
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert (corpo["username"], corpo["nome"], corpo["perfil"], corpo["ativo"]) == \
        ("joao.silva", "João da Silva", "RECEPCAO", True)

    assert [u["username"] for u in client.get(URL, headers=_chefia()).json()] == ["admin", "joao.silva"]
    assert _auditoria(client) == [("admin", "SEGURANCA", "INCLUIR_USUARIO", "usuario:joao.silva", None,
                                   {"nome": "João da Silva", "perfil": "RECEPCAO", "ativo": True}, "testclient")]
    # O novo usuário já consegue usar o SAP com o perfil concedido.
    me = client.get("/api/users/me", headers=_h("joao.silva", "RECEPCAO"))
    assert me.status_code == 200 and me.json()["role"] == "RECEPCAO"


def test_inclusao_recusa_duplicado_login_fora_do_ad_e_perfil_invalido(client):
    _autorizar(client, "joao.silva", "RECEPCAO", ativo=False)
    assert client.post(URL, json={"username": "joao.silva", "perfil": "RESIDENTE"},
                       headers=_chefia()).status_code == 409
    assert client.post(URL, json={"username": "inexistentuser999", "perfil": "RECEPCAO"},
                       headers=_chefia()).status_code == 404
    assert client.post(URL, json={"username": "maria.souza", "perfil": "ADMINISTRADOR"},
                       headers=_chefia()).status_code == 400
    assert _auditoria(client) == []


def test_inclusao_respeita_mapa_de_grupos_do_ad(client, monkeypatch):
    mapa = {p: ["GRUPO-" + p] for p in ("RECEPCAO", "LABORATORIO", "RESIDENTE", "PRECEPTORIA", "CHEFIA")}
    monkeypatch.setenv("SAP_ROLE_GROUP_MAP", json.dumps(mapa))
    chefia = _h("admin", "CHEFIA", ["GRUPO-CHEFIA"])
    # maria.souza não tem o grupo exigido para RECEPCAO no AD (Mock).
    r = client.post(URL, json={"username": "maria.souza", "perfil": "RECEPCAO"}, headers=chefia)
    assert r.status_code == 409 and "grupo" in r.json()["detail"]


def test_inclusao_e_auditoria_na_mesma_transacao(client, monkeypatch):
    async def _falha(*args, **kwargs):
        raise RuntimeError("falha simulada na auditoria")
    monkeypatch.setattr(usuario_controller, "registrar_auditoria", _falha)
    with pytest.raises(RuntimeError):
        client.post(URL, json={"username": "maria.souza", "perfil": "RECEPCAO"}, headers=_chefia())
    with sqlite3.connect(_db(client)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM authorized_users WHERE username='maria.souza'").fetchone()[0] == 0


# ------------------------------------------------------------------ perfil
def test_altera_perfil_com_auditoria_e_efeito_imediato(client):
    _autorizar(client, "joao.silva", "RECEPCAO")
    r = client.patch(f"{URL}/joao.silva/perfil", json={"perfil": "LABORATORIO"}, headers=_chefia())
    assert r.status_code == 200, r.text
    assert r.json()["perfil"] == "LABORATORIO" and r.json()["atualizado_em"]
    assert _auditoria(client)[-1][2:6] == ("ALTERAR_PERFIL_USUARIO", "usuario:joao.silva",
                                          {"perfil": "RECEPCAO"}, {"perfil": "LABORATORIO"})
    # Token antigo (RECEPCAO) passa a valer com o perfil do banco.
    assert client.get("/api/users/me", headers=_h("joao.silva", "RECEPCAO")).json()["role"] == "LABORATORIO"


def test_perfil_recusa_auto_alteracao_mesmo_perfil_e_inexistente(client):
    _autorizar(client, "joao.silva", "RECEPCAO")
    r = client.patch(f"{URL}/admin/perfil", json={"perfil": "RECEPCAO"}, headers=_chefia())
    assert r.status_code == 403 and "próprio" in r.json()["detail"]
    assert client.patch(f"{URL}/joao.silva/perfil", json={"perfil": "RECEPCAO"},
                        headers=_chefia()).status_code == 409
    assert client.patch(f"{URL}/ninguem.aqui/perfil", json={"perfil": "RECEPCAO"},
                        headers=_chefia()).status_code == 404
    assert _auditoria(client) == []


# ------------------------------------------------------------------ situação
def test_inativa_e_reativa_sem_apagar(client):
    _autorizar(client, "joao.silva", "RECEPCAO")
    r = client.patch(f"{URL}/joao.silva/situacao", json={"ativo": False}, headers=_chefia())
    assert r.status_code == 200 and r.json()["ativo"] is False
    assert client.get("/api/users/me", headers=_h("joao.silva", "RECEPCAO")).status_code == 403
    assert "joao.silva" in [u["username"] for u in client.get(URL, headers=_chefia()).json()]

    assert client.patch(f"{URL}/joao.silva/situacao", json={"ativo": False}, headers=_chefia()).status_code == 409
    assert client.patch(f"{URL}/joao.silva/situacao", json={"ativo": True}, headers=_chefia()).json()["ativo"] is True
    assert [e[2] for e in _auditoria(client)] == ["INATIVAR_USUARIO", "REATIVAR_USUARIO"]


def test_chefia_nao_inativa_a_si_mesma(client):
    r = client.patch(f"{URL}/admin/situacao", json={"ativo": False}, headers=_chefia())
    assert r.status_code == 403
    assert client.get("/api/users/me", headers=_chefia()).status_code == 200
