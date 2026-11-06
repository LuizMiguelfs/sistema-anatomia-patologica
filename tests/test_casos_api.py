"""Módulo de casos pela API, no SQLite real (migração aplicada) e com o AGHU simulado."""
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from src.auth.auth import auth_handler
from src.controllers import caso_controller
from src.dependencies import get_aghu_solicitacao_provider
from src.main import app
from src.providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface


class AghuFalso(AghuSolicitacaoProviderInterface):
    """AGHU simulado com uma solicitação (123) de duas amostras."""

    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Cabeçalho da solicitação 123."""
        if solicitacao_aghu != "123":
            return None
        return {"solicitacao_aghu": 123, "paciente_codigo_aghu": 9, "paciente_nome": "MARIA DA SILVA",
                "prontuario_aghu": "19033448"}

    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        """Duas amostras."""
        return [{"amostra_aghu": 1, "descricao": "BIOPSIA"}, {"amostra_aghu": 2, "descricao": "PECA"}]


def _h(username: str, role: str) -> Dict[str, str]:
    """Cabeçalho com token de acesso."""
    token = auth_handler.create_access_token({"username": username, "role": role, "groups": ["Users"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Banco migrado (Alembic), usuários RECEPCAO e LABORATORIO e AGHU simulado."""
    db = tmp_path / "app.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db}")
    command.upgrade(Config("alembic.ini"), "head")
    monkeypatch.setattr(caso_controller, "_ano_local", lambda: 2026)
    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: AghuFalso()
    try:
        with TestClient(app) as client:
            with sqlite3.connect(db) as conn:
                for user, role in (("ana.recepcao", "RECEPCAO"), ("bia.lab", "LABORATORIO")):
                    conn.execute("INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, 1, ?)",
                                 (user, role, datetime.now(timezone.utc).isoformat()))
            yield client, db
    finally:
        app.dependency_overrides.pop(get_aghu_solicitacao_provider, None)


def test_fluxo_completo_pela_api(api):
    client, db = api
    rec = _h("ana.recepcao", "RECEPCAO")

    previa = client.get("/api/casos/aghu/solicitacao/123", headers=rec)
    assert previa.status_code == 200, previa.text
    assert previa.json()["caso_existente"] is None and len(previa.json()["amostras"]) == 2

    r = client.post("/api/casos", json={"solicitacao_aghu": "123", "tipo_exame": "HP"}, headers=rec)
    assert r.status_code == 201, r.text
    caso = r.json()
    assert caso["identificador_interno"] == "HP-0001/26"
    assert caso["etapa_atual"] == "RECEPCAO" and caso["acoes"]["pode_concluir"] is True

    assert client.post("/api/casos", json={"solicitacao_aghu": "123", "tipo_exame": "HP"}, headers=rec).status_code == 409

    lista = client.get("/api/casos", params={"solicitacao": "123"}, headers=rec).json()
    assert lista["total"] == 1 and lista["items"][0]["identificador_interno"] == "HP-0001/26"

    r = client.post(f"/api/casos/{caso['id']}/concluir-etapa", headers=rec)
    assert r.status_code == 200 and r.json()["etapa_atual"] == "MACROSCOPIA"
    assert client.post(f"/api/casos/{caso['id']}/concluir-etapa", headers=rec).status_code == 403  # alçada

    hist = client.get(f"/api/casos/{caso['id']}/historico", headers=_h("bia.lab", "LABORATORIO")).json()
    assert [m["tipo"] for m in hist] == ["ABERTURA", "CONCLUSAO"]

    with sqlite3.connect(db) as conn:
        acoes = [r[0] for r in conn.execute("SELECT acao FROM audit_logs WHERE recurso = ?", (f"caso:{caso['id']}",))]
    assert acoes == ["ABRIR_CASO", "CONCLUIR_ETAPA"]


def test_exige_autenticacao(api):
    client, _ = api
    assert client.get("/api/casos").status_code == 401
