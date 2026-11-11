"""MVP pela API (SQLite migrado + AGHU simulado): Solicitações de Exames e fases do setor."""
import sqlite3
from datetime import datetime, timedelta, timezone
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

SOLICITACOES = {
    "101": {"tipo_exame": "HP", "prontuario_aghu": "11110001", "paciente_nome": "PACIENTE FICTICIO UM"},
    "102": {"tipo_exame": "CO", "prontuario_aghu": "11110002", "paciente_nome": "PACIENTE FICTICIO DOIS"},
    "103": {"tipo_exame": "HP", "prontuario_aghu": "11110003", "paciente_nome": "PACIENTE FICTICIO TRES"},
}


class AghuFalso(AghuSolicitacaoProviderInterface):
    """AGHU simulado com três solicitações (HP, CO e HP)."""

    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Cabeçalho da solicitação fictícia."""
        dados = SOLICITACOES.get(solicitacao_aghu)
        return {"solicitacao_aghu": int(solicitacao_aghu), "paciente_codigo_aghu": 1, **dados} if dados else None

    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        """Duas amostras."""
        return [{"amostra_aghu": 1, "descricao": "Biópsia A"}, {"amostra_aghu": 2, "descricao": "Biópsia B"}]


def _h(username: str, role: str) -> Dict[str, str]:
    """Cabeçalho com token de acesso."""
    token = auth_handler.create_access_token({"username": username, "role": role, "groups": ["Users"]})
    return {"Authorization": f"Bearer {token}"}


REC = _h("ana.recepcao", "RECEPCAO")
LAB = _h("bia.lab", "LABORATORIO")
RES = _h("caio.res", "RESIDENTE")
PAT = _h("dora.pat", "PRECEPTORIA")
CHE = _h("eva.chefia", "CHEFIA")


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Banco migrado, um usuário por perfil, AGHU simulado e três solicitações recebidas."""
    db = tmp_path / "app.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db}")
    command.upgrade(Config("alembic.ini"), "head")
    monkeypatch.setattr(caso_controller, "_ano_local", lambda: 2026)
    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: AghuFalso()
    try:
        with TestClient(app) as client:
            with sqlite3.connect(db) as conn:
                for user, role in (("ana.recepcao", "RECEPCAO"), ("bia.lab", "LABORATORIO"), ("caio.res", "RESIDENTE"),
                                   ("dora.pat", "PRECEPTORIA"), ("eva.chefia", "CHEFIA")):
                    conn.execute("INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, 1, ?)",
                                 (user, role, datetime.now(timezone.utc).isoformat()))
            ids = {}
            for numero in ("101", "102", "103"):
                r = client.post("/api/casos", json={"solicitacao_aghu": numero}, headers=REC)
                assert r.status_code == 201, r.text
                ids[numero] = r.json()["id"]
            yield client, db, ids
    finally:
        app.dependency_overrides.pop(get_aghu_solicitacao_provider, None)


def _nao_retirados(client, **params):
    """Lista "Não retirados"."""
    r = client.get("/api/solicitacoes", params={"situacao": "NAO_RETIRADO", **params}, headers=REC)
    assert r.status_code == 200, r.text
    return r.json()


def test_nao_retirados_urgencia_no_topo_e_colunas(api):
    client, _, _ = api
    corpo = _nao_retirados(client)
    assert [i["solicitacao_aghu"] for i in corpo["items"]] == ["102", "101", "103"]  # CO urgente primeiro
    primeiro = corpo["items"][0]
    assert primeiro["urgente"] is True and primeiro["identificador_interno"] == "CO-0001/26"
    assert primeiro["prontuario_aghu"] == "11110002" and primeiro["qtd_amostras"] == 2
    assert "Biópsia A" in primeiro["descricao_amostras"]


def test_busca_pelos_tres_codigos_e_filtro_por_tipo(api):
    client, _, _ = api
    assert _nao_retirados(client, busca="11110001")["items"][0]["solicitacao_aghu"] == "101"  # prontuário
    assert _nao_retirados(client, busca="103")["items"][0]["solicitacao_aghu"] == "103"  # código AGHU
    assert _nao_retirados(client, busca="hp-0002/26")["items"][0]["solicitacao_aghu"] == "103"  # código interno
    assert _nao_retirados(client, tipo_exame="CO")["total"] == 1
    assert client.get("/api/solicitacoes", params={"de": "11/11/2026"}, headers=REC).status_code == 422


def test_retirar_so_recepcao_e_desfazer(api):
    client, _, ids = api
    assert client.post(f"/api/solicitacoes/{ids['101']}/retirar", headers=LAB).status_code == 403
    r = client.post(f"/api/solicitacoes/{ids['101']}/retirar", headers=REC)
    assert r.status_code == 200 and r.json()["etapa_atual"] == "MACROSCOPIA"
    assert client.post(f"/api/solicitacoes/{ids['101']}/retirar", headers=REC).status_code == 409

    retirados = client.get("/api/solicitacoes", params={"situacao": "RETIRADO"}, headers=REC).json()
    assert [i["solicitacao_aghu"] for i in retirados["items"]] == ["101"]
    assert retirados["items"][0]["retirado_por"] == "ana.recepcao"
    assert _nao_retirados(client)["total"] == 2

    r = client.post(f"/api/solicitacoes/{ids['101']}/desfazer-retirada", headers=REC)
    assert r.status_code == 200 and r.json()["etapa_atual"] == "RECEPCAO"
    assert _nao_retirados(client)["total"] == 3

    # Depois que a fase seguinte salva algo, não dá mais para desfazer.
    client.post(f"/api/solicitacoes/{ids['101']}/retirar", headers=REC)
    client.put(f"/api/fases/MACROSCOPIA/solicitacoes/{ids['101']}", json={"dados": {"qtd_fragmentos": 1}}, headers=RES)
    assert client.post(f"/api/solicitacoes/{ids['101']}/desfazer-retirada", headers=REC).status_code == 409


def test_fila_mostra_so_a_fase_atual(api):
    client, _, ids = api
    client.post(f"/api/solicitacoes/{ids['101']}/retirar", headers=REC)
    client.post(f"/api/solicitacoes/{ids['102']}/retirar", headers=REC)
    macro = client.get("/api/fases/MACROSCOPIA/fila", headers=CHE).json()
    assert [i["solicitacao_aghu"] for i in macro["items"]] == ["101"]
    assert client.get("/api/fases/MICROSCOPIA/fila", headers=CHE).json()["total"] == 0
    assert client.get("/api/fases/CONGELACAO/fila", headers=CHE).json()["items"][0]["urgente"] is True
    assert client.get("/api/fases/INEXISTENTE/fila", headers=CHE).status_code == 404


def test_salvar_concluir_obrigatorios_e_perfis(api):
    client, db, ids = api
    caso = ids["101"]
    client.post(f"/api/solicitacoes/{caso}/retirar", headers=REC)
    url = f"/api/fases/MACROSCOPIA/solicitacoes/{caso}"

    assert client.put(url, json={"dados": {"qtd_fragmentos": 2}}, headers=LAB).status_code == 403
    assert client.put(url, json={"dados": {"campo_que_nao_existe": "x"}}, headers=RES).status_code == 422
    r = client.put(url, json={"dados": {"qtd_fragmentos": 2}}, headers=RES)  # Salvar sem obrigatórios
    assert r.status_code == 200 and r.json()["situacao"] == "RASCUNHO" and r.json()["pendente"] is True

    r = client.post(f"{url}/concluir", json={"dados": {}}, headers=RES)
    assert r.status_code == 422 and "Descrição macroscópica" in r.json()["detail"]

    completo = {"descricao_macroscopica": "Fragmento", "qtd_cassetes": 1, "laudo_macroscopico": "Laudo"}
    r = client.post(f"{url}/concluir", json={"dados": completo}, headers=RES)
    assert r.status_code == 200, r.text
    assert r.json()["situacao"] == "CONCLUIDA" and r.json()["dados"]["qtd_fragmentos"] == 2
    assert r.json()["solicitacao"]["etapa_atual"] == "PROCESSAMENTO"

    # Concluída continua na mesma fila (não pendente) e ainda pode ser editada.
    fila = client.get("/api/fases/MACROSCOPIA/fila", headers=RES).json()["items"]
    assert fila[0]["pendente"] is False and fila[0]["editavel_ate"]
    r = client.put(url, json={"dados": {"observacoes": "corrigido"}}, headers=RES)
    assert r.status_code == 200 and r.json()["situacao"] == "CONCLUIDA"
    assert client.put(url, json={"dados": {"laudo_macroscopico": ""}}, headers=RES).status_code == 422  # não esvazia
    assert client.get("/api/fases/PROCESSAMENTO/fila", headers=LAB).json()["items"][0]["solicitacao_aghu"] == "101"

    # Passados 6 dias, sai da fila e não aceita mais edição.
    antigo = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE caso_fases SET concluido_em = ? WHERE caso_id = ?", (antigo, caso))
    assert client.get("/api/fases/MACROSCOPIA/fila", headers=RES).json()["total"] == 0
    assert client.put(url, json={"dados": {"observacoes": "tarde"}}, headers=RES).status_code == 409

    with sqlite3.connect(db) as conn:
        acoes = [r[0] for r in conn.execute("SELECT acao FROM audit_logs WHERE recurso = ?", (f"caso:{caso}",))]
    assert "SALVAR_MACROSCOPIA" in acoes and "CONCLUIR_MACROSCOPIA" in acoes and "EDITAR_CONCLUIDA_MACROSCOPIA" in acoes


def test_microscopia_residente_preenche_e_patologista_conclui(api):
    client, _, ids = api
    caso = ids["101"]
    client.post(f"/api/solicitacoes/{caso}/retirar", headers=REC)
    client.post(f"/api/fases/MACROSCOPIA/solicitacoes/{caso}/concluir", headers=RES, json={"dados": {
        "descricao_macroscopica": "F", "qtd_fragmentos": 1, "qtd_cassetes": 1, "laudo_macroscopico": "L"}})
    client.post(f"/api/fases/PROCESSAMENTO/solicitacoes/{caso}/concluir", headers=LAB, json={"dados": {
        "inicio": "Histotécnico", "qtd_blocos": 1, "qtd_laminas": 2}})
    url = f"/api/fases/MICROSCOPIA/solicitacoes/{caso}"

    r = client.put(url, json={"dados": {"pre_laudo": "Pré-laudo", "diagnostico": "tentativa do residente"}}, headers=RES)
    assert r.status_code == 200 and r.json()["dados"]["diagnostico"] is None  # campo só do patologista
    assert r.json()["pode_concluir"] is False
    assert client.post(f"{url}/concluir", json={"dados": {}}, headers=RES).status_code == 403

    visao_pat = client.get(url, headers=PAT).json()
    assert visao_pat["pode_concluir"] is True
    assert next(c for c in visao_pat["campos"] if c["nome"] == "diagnostico")["editavel"] is True

    r = client.post(f"{url}/concluir", json={"dados": {"diagnostico": "Diagnóstico final"}}, headers=PAT)
    assert r.status_code == 200 and r.json()["solicitacao"]["etapa_atual"] == "ARQUIVO"


def test_ihq_pedida_na_microscopia_volta_para_microscopia(api):
    client, _, ids = api
    caso = ids["103"]
    client.post(f"/api/solicitacoes/{caso}/retirar", headers=REC)
    client.post(f"/api/fases/MACROSCOPIA/solicitacoes/{caso}/concluir", headers=RES, json={"dados": {
        "descricao_macroscopica": "F", "qtd_fragmentos": 1, "qtd_cassetes": 1, "laudo_macroscopico": "L"}})
    client.post(f"/api/fases/PROCESSAMENTO/solicitacoes/{caso}/concluir", headers=LAB, json={"dados": {
        "inicio": "Preparo manual", "qtd_blocos": 1, "qtd_laminas": 1}})
    r = client.post(f"/api/casos/{caso}/encaminhar", json={"destino": "IHQ", "motivo": "painel"}, headers=PAT)
    assert r.status_code == 200 and r.json()["etapa_atual"] == "IHQ"

    assert [i["solicitacao_aghu"] for i in client.get("/api/fases/IHQ/fila", headers=LAB).json()["items"]] == ["103"]
    r = client.post(f"/api/fases/IHQ/solicitacoes/{caso}/concluir", headers=LAB, json={"dados": {
        "marcadores": "CK7, CK20", "qtd_laminas": 2, "resultado": "Laudo da IHQ"}})
    assert r.status_code == 200 and r.json()["solicitacao"]["etapa_atual"] == "MICROSCOPIA"


def test_definicoes_dos_formularios(api):
    client, _, _ = api
    fases = client.get("/api/fases", headers=CHE).json()
    assert [f["etapa"] for f in fases] == ["MACROSCOPIA", "CONGELACAO", "PROCESSAMENTO", "IHQ", "MICROSCOPIA", "REVISAO"]
    assert fases[0]["dias_edicao_apos_conclusao"] == 6
    assert client.get("/api/fases").status_code == 401  # Default-Private
