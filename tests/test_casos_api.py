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
                "prontuario_aghu": "19033448", "tipo_exame": "HP"}

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
    assert previa.json()["tipo_exame"] == "HP"
    assert client.post("/api/casos", json={"solicitacao_aghu": "123", "tipo_exame": "CO"}, headers=rec).status_code in (400, 422)

    r = client.post("/api/casos", json={"solicitacao_aghu": "123"}, headers=rec)
    assert r.status_code == 201, r.text
    caso = r.json()
    assert caso["identificador_interno"] == "HP-0001/26"
    assert caso["etapa_atual"] == "RECEPCAO" and caso["acoes"]["pode_concluir"] is True

    assert client.post("/api/casos", json={"solicitacao_aghu": "123"}, headers=rec).status_code == 409

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


def test_dados_do_paciente_cifrados_e_busca_por_prontuario(api):
    client, db = api
    rec = _h("ana.recepcao", "RECEPCAO")
    caso = client.post("/api/casos", json={"solicitacao_aghu": "123"}, headers=rec).json()
    assert caso["paciente_nome"] == "MARIA DA SILVA" and caso["prontuario_aghu"] == "19033448"

    with sqlite3.connect(db) as conn:
        nome, prontuario, indice, codigo = conn.execute(
            "SELECT paciente_nome, prontuario_aghu, prontuario_indice, paciente_codigo_aghu FROM casos").fetchone()
    assert nome.startswith("aes256gcm:v1:") and prontuario.startswith("aes256gcm:v1:")
    assert "MARIA" not in nome and "19033448" not in prontuario + indice
    assert codigo == "9"  # chave técnica do AGHU, em claro

    # Prontuário como aparece na Ficha de Trabalho ("1903344/8") ou só com dígitos.
    for termo in ("1903344/8", "19033448"):
        pagina = client.get("/api/casos", params={"prontuario": termo}, headers=rec).json()
        assert pagina["total"] == 1 and pagina["items"][0]["paciente_nome"] == "MARIA DA SILVA"
    assert client.get("/api/casos", params={"prontuario": "11111111"}, headers=rec).json()["total"] == 0



def test_conferencia_e_sincronizacao_cadastral_auditada(api):
    client, db = api
    rec = _h("ana.recepcao", "RECEPCAO")
    caso = client.post("/api/casos", json={"solicitacao_aghu": "123"}, headers=rec).json()
    ident = caso["id"]

    class AghuComCorrecao(AghuFalso):
        async def buscar_solicitacao(self, solicitacao_aghu: str):
            dados = await super().buscar_solicitacao(solicitacao_aghu)
            return {**dados, "paciente_nome": "MARIA SILVA ATUALIZADA", "prontuario_aghu": "55555555"} if dados else None

    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: AghuComCorrecao()

    previa = client.get(f"/api/casos/{ident}/conferencia-aghu", headers=rec)
    assert previa.status_code == 200
    assert previa.json()["atualizacao_pendente"] is True
    assert set(previa.json()["divergencias"]) == {"paciente_nome", "prontuario_aghu"}

    lab = _h("bia.lab", "LABORATORIO")
    assert client.get(f"/api/casos/{ident}/conferencia-aghu", headers=lab).status_code == 403
    assert client.post(f"/api/casos/{ident}/sincronizar-aghu", headers=lab).status_code == 403

    resposta = client.post(f"/api/casos/{ident}/sincronizar-aghu", headers=rec)
    assert resposta.status_code == 200, resposta.text
    atualizado = resposta.json()
    assert atualizado["paciente_nome"] == "MARIA SILVA ATUALIZADA"
    assert atualizado["prontuario_aghu"] == "55555555"
    assert atualizado["ultima_sincronizacao_aghu"]

    with sqlite3.connect(db) as conn:
        nome_cifrado, prontuario_cifrado = conn.execute(
            "SELECT paciente_nome, prontuario_aghu FROM casos WHERE id=?", (ident,)
        ).fetchone()
        assert "MARIA" not in nome_cifrado and "55555" not in prontuario_cifrado
        auditoria = conn.execute(
            "SELECT dados_anteriores, dados_novos FROM audit_logs "
            "WHERE acao='SINCRONIZAR_CADASTRO_AGHU' AND recurso=?", (f"caso:{ident}",)
        ).fetchone()
        assert auditoria
        assert "MARIA" not in auditoria[0] + auditoria[1]
        movimentos = [r[0] for r in conn.execute(
            "SELECT tipo FROM caso_movimentacoes WHERE caso_id=? ORDER BY id", (ident,)
        )]
        assert movimentos[-1] == "SINCRONIZACAO_AGHU"
    assert client.get(f"/api/casos/{ident}/conferencia-aghu", headers=rec).json()["atualizacao_pendente"] is False


def test_mudanca_vinculo_ou_tipo_exige_analise_sem_alterar_dados(api):
    client, _ = api
    rec = _h("ana.recepcao", "RECEPCAO")
    caso = client.post("/api/casos", json={"solicitacao_aghu": "123"}, headers=rec).json()

    class AghuComTroca(AghuFalso):
        async def buscar_solicitacao(self, solicitacao_aghu: str):
            dados = await super().buscar_solicitacao(solicitacao_aghu)
            return {**dados, "paciente_codigo_aghu": 456, "tipo_exame": "CO"} if dados else None

    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: AghuComTroca()
    assert client.get(f"/api/casos/{caso['id']}/conferencia-aghu", headers=rec).status_code == 409
    assert client.post(f"/api/casos/{caso['id']}/sincronizar-aghu", headers=rec).status_code == 409
    assert client.get(f"/api/casos/{caso['id']}", headers=rec).json()["paciente_nome"] == "MARIA DA SILVA"


def test_tipo_ausente_bloqueia_abertura_sem_registro(api):
    client, _ = api
    rec = _h("ana.recepcao", "RECEPCAO")

    class AghuSemTipo(AghuFalso):
        async def buscar_solicitacao(self, solicitacao_aghu: str):
            dados = await super().buscar_solicitacao(solicitacao_aghu)
            return {**dados, "tipo_exame": None} if dados else None

    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: AghuSemTipo()
    r = client.post("/api/casos", json={"solicitacao_aghu": "123"}, headers=rec)
    assert r.status_code == 409
    assert client.get("/api/casos", headers=rec).json()["total"] == 0
