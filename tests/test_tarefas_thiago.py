"""Testes de regressão das tarefas T04, T05 e T08 em banco SQLite migrado e AGHU simulado.

Nunca acessa pacientes reais ou o AD institucional. A liberação AGHU é FICTÍCIA.
"""
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from src.auth.auth import auth_handler
from src.controllers import laudo_controller, solicitacao_controller
from src.dependencies import get_aghu_solicitacao_provider
from src.main import app
from src.providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface

USERS = (
    ("ana.recepcao", "RECEPCAO"),
    ("bia.lab", "LABORATORIO"),
    ("caio.res", "RESIDENTE"),
    ("dora.pat", "PRECEPTORIA"),
    ("eva.chefia", "CHEFIA"),
)


def auth(username: str, role: str) -> Dict[str, str]:
    token = auth_handler.create_access_token({"username": username, "role": role, "groups": ["Users"]})
    return {"Authorization": f"Bearer {token}"}


REC = auth(*USERS[0]); LAB = auth(*USERS[1]); RES = auth(*USERS[2]); PAT = auth(*USERS[3]); CHE = auth(*USERS[4])
CREDS = {"username": "ana.recepcao", "password": "admin"}


class AghuFicticio(AghuSolicitacaoProviderInterface):
    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        if solicitacao_aghu != "887766":
            return None
        return {"solicitacao_aghu": 887766, "paciente_codigo_aghu": 101,
                "paciente_nome": "PACIENTE FICTICIO", "prontuario_aghu": "10011223", "tipo_exame": "HP"}

    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        return [{"amostra_aghu": "1", "descricao": "Amostra fictícia A"}]


@pytest.fixture
def cenario(tmp_path, monkeypatch):
    db = tmp_path / "thiago.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db}")
    monkeypatch.setenv("AGHU_PROVIDER_TYPE", "SIMULADO")
    command.upgrade(Config("alembic.ini"), "head")
    monkeypatch.setattr(solicitacao_controller, "_ano_local", lambda: 2026)
    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: AghuFicticio()
    try:
        with TestClient(app) as client:
            with sqlite3.connect(db) as conn:
                for username, role in USERS:
                    conn.execute(
                        "INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, 1, ?)",
                        (username, role, datetime.now(timezone.utc).isoformat()),
                    )
            resposta = client.post("/api/solicitacoes", json={"solicitacao_aghu": "887766"}, headers=REC)
            assert resposta.status_code == 201, resposta.text
            yield client, db, resposta.json()["id"]
    finally:
        app.dependency_overrides.pop(get_aghu_solicitacao_provider, None)


def _retirar(client: TestClient, sid: int, header: Dict[str, str] = LAB, credenciais=None):
    return client.post(f"/api/solicitacoes/{sid}/retirar", headers=header,
                       json=credenciais if credenciais is not None else CREDS)


def test_t04_retirada_por_identidade_propria_em_estacao_alheia(cenario):
    client, db, sid = cenario
    # Sessão da estação é de Laboratório, mas foi a recepcionista que digitou sua própria senha.
    resposta = _retirar(client, sid, LAB)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["retirado_por"] == "ana.recepcao"
    historico = client.get(f"/api/solicitacoes/{sid}/historico", headers=CHE).json()
    assert [i["tipo"] for i in historico][-1] == "RETIRADA"
    assert historico[-1]["usuario"] == "ana.recepcao"
    with sqlite3.connect(db) as con:
        log = con.execute("SELECT usuario, dados_novos FROM audit_logs WHERE acao = 'MARCAR_RETIRADO'").fetchone()
    assert log[0] == "ana.recepcao"
    assert "bia.lab" in str(log[1])  # Identidade da estação registrada, sem senha.
    assert "admin" not in str(log[1])
    assert _retirar(client, sid, LAB).status_code == 409  # impede retirada duplicada
    desfeito = client.post(f"/api/solicitacoes/{sid}/desfazer-retirada", headers=LAB, json=CREDS)
    assert desfeito.status_code == 200, desfeito.text
    assert desfeito.json()["retirado_por"] is None


def test_t04_senha_errada_perfil_invalido_e_sessao_anonima_nao_mutam(cenario):
    client, db, sid = cenario
    assert _retirar(client, sid, LAB, {"username": "ana.recepcao", "password": "errada"}).status_code == 401
    assert _retirar(client, sid, LAB, {"username": "bia.lab", "password": "admin"}).status_code == 403
    assert client.post(f"/api/solicitacoes/{sid}/retirar", json=CREDS).status_code == 401
    with sqlite3.connect(db) as con:
        row = con.execute("SELECT retirado_por, retirado_em FROM solicitacoes_exame WHERE id = ?", (sid,)).fetchone()
    assert row == (None, None)


def test_t05_matriz_inicial_autenticada_e_regras_do_backend(cenario):
    client, _, sid = cenario
    assert client.get("/api/permissoes").status_code == 401
    resposta = client.get("/api/permissoes", headers=CHE)
    assert resposta.status_code == 200, resposta.text
    matriz = resposta.json()["matriz"]
    assert matriz["homologada_pelo_hc"] is False
    assert matriz["retirada_credencial"] == ["RECEPCAO"]
    assert matriz["liberar_laudo"] == ["PRECEPTORIA"]
    assert matriz["fases"]["MICROSCOPIA"]["editar"] == ["RESIDENTE", "PRECEPTORIA"]
    assert matriz["fases"]["MICROSCOPIA"]["concluir"] == ["PRECEPTORIA"]
    assert resposta.json()["usuario"]["pode_liberar_laudo"] is False
    assert client.get("/api/permissoes", headers=PAT).json()["usuario"]["pode_liberar_laudo"] is True
    # Nem a Chefia ganha implicitamente direito de alterar etapas clínicas.
    assert client.post(f"/api/solicitacoes/{sid}/retirar", headers=CHE,
                       json={"username": "eva.chefia", "password": "admin"}).status_code == 403


def _ate_revisao(client: TestClient, sid: int):
    assert _retirar(client, sid, LAB).status_code == 200
    base = f"/api/fases/MACROSCOPIA/solicitacoes/{sid}/concluir"
    r = client.post(base, headers=RES, json={"dados": {
        "descricao_macroscopica": "Descrição fictícia", "qtd_fragmentos": 1,
        "qtd_cassetes": 1, "laudo_macroscopico": "Macroscopia fictícia"}})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/fases/PROCESSAMENTO/solicitacoes/{sid}/concluir", headers=LAB, json={"dados": {
        "inicio": "Histotécnico", "qtd_blocos": 1, "qtd_laminas": 1}})
    assert r.status_code == 200, r.text
    r = client.put(f"/api/fases/MICROSCOPIA/solicitacoes/{sid}", headers=RES,
                   json={"dados": {"pre_laudo": "Pré-laudo fictício"}})
    assert r.status_code == 200, r.text


def test_t08_revisao_liberacao_simulada_arquivo_e_historico(cenario):
    client, db, sid = cenario
    _ate_revisao(client, sid)
    lista = client.get("/api/laudos/revisoes", headers=PAT)
    assert lista.status_code == 200, lista.text
    assert len(lista.json()) == 1 and lista.json()[0]["id"] == sid
    assert lista.json()[0]["situacao_revisao"] == "EM_REVISAO"
    assert "dados" not in lista.json()[0]
    assert client.post(f"/api/laudos/solicitacoes/{sid}/arquivar", headers=PAT).status_code == 409
    r = client.post(f"/api/fases/MICROSCOPIA/solicitacoes/{sid}/concluir", headers=PAT,
                    json={"dados": {"diagnostico": "Diagnóstico fictício validado"}})
    assert r.status_code == 200, r.text
    assert r.json()["solicitacao"]["etapa_atual"] == "AGUARDANDO_LIBERACAO"
    assert client.get("/api/laudos/revisoes", headers=PAT).json() == []
    assert client.get("/api/laudos/solicitacoes/"+str(sid), headers=PAT).json()["documentos"] == []
    pendentes = client.get("/api/laudos/pendentes-liberacao", headers=PAT).json()
    assert len(pendentes) == 1 and pendentes[0]["status"] == "AGUARDANDO_LIBERACAO"
    assert client.post(f"/api/laudos/solicitacoes/{sid}/liberacao-simulada", headers=RES).status_code == 403
    r = client.post(f"/api/laudos/solicitacoes/{sid}/liberacao-simulada", headers=PAT)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "LIBERADO"
    assert any(d["conteudo"] == "Diagnóstico fictício validado" for d in r.json()["documentos"])
    assert client.post(f"/api/laudos/solicitacoes/{sid}/liberacao-simulada", headers=PAT).status_code == 409
    r = client.post(f"/api/laudos/solicitacoes/{sid}/arquivar", headers=PAT)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "ARQUIVADO"
    assert client.post(f"/api/laudos/solicitacoes/{sid}/arquivar", headers=PAT).status_code == 409
    assert client.get("/api/solicitacoes", params={"situacao": "ARQUIVADO"}, headers=CHE).json()["total"] == 1
    assert client.get("/api/solicitacoes", params={"situacao": "RETIRADO"}, headers=CHE).json()["total"] == 0
    hist = client.get(f"/api/solicitacoes/{sid}/historico", headers=CHE).json()
    tipos = [m["tipo"] for m in hist]
    assert tipos[-2:] == ["LIBERACAO_DEMO", "ARQUIVAMENTO"]
    with sqlite3.connect(db) as con:
        evento = con.execute("SELECT fonte, referencia, liberado_por, arquivado_por FROM solicitacao_liberacoes WHERE solicitacao_id = ?", (sid,)).fetchone()
    assert evento == ("DEMONSTRACAO", f"DEMO-AGHU-{sid}", "dora.pat", "dora.pat")


def test_t08_liberacao_ficticia_bloqueada_em_ambiente_real(cenario, monkeypatch):
    client, _, sid = cenario
    _ate_revisao(client, sid)
    r = client.post(f"/api/fases/MICROSCOPIA/solicitacoes/{sid}/concluir", headers=PAT,
                    json={"dados": {"diagnostico": "Diagnóstico fictício validado"}})
    assert r.status_code == 200, r.text
    monkeypatch.setattr(laudo_controller, "ENV", "production")
    assert client.post(f"/api/laudos/solicitacoes/{sid}/liberacao-simulada", headers=PAT).status_code == 403


def test_t04_sql_nao_reexecuta_retirada_confirmada(cenario):
    """O UPDATE atômico impede sobrescrever a identidade de uma retirada já feita."""
    from pathlib import Path

    _client, db, sid = cenario
    sql = Path('src/providers/sql/solicitacao/marcar_retirada.sql').read_text(encoding='utf-8')
    parametros = {
        'solicitacao_id': sid, 'etapa_atual': 'MACROSCOPIA', 'status': 'EM_ANDAMENTO',
        'usuario': 'ana.recepcao', 'agora': datetime.now(timezone.utc).isoformat(),
    }
    with sqlite3.connect(db) as con:
        assert con.execute(sql, parametros).rowcount == 1
        assert con.execute(sql, {**parametros, 'usuario': 'outra.pessoa'}).rowcount == 0
        assert con.execute('SELECT retirado_por FROM solicitacoes_exame WHERE id=?', (sid,)).fetchone() == ('ana.recepcao',)


def test_t04_sql_nao_desfaz_apos_inicio_da_fase(cenario):
    """A guarda no banco protege contra alteração entre a leitura e a confirmação da API."""
    from pathlib import Path

    client, db, sid = cenario
    assert _retirar(client, sid).status_code == 200
    sql = Path('src/providers/sql/solicitacao/desfazer_retirada.sql').read_text(encoding='utf-8')
    with sqlite3.connect(db) as con:
        con.execute(
            'INSERT INTO solicitacao_fases (solicitacao_id, etapa, dados, situacao, salvo_por, salvo_em) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (sid, 'MACROSCOPIA', '{}', 'RASCUNHO', 'caio.res', datetime.now(timezone.utc).isoformat()),
        )
        resposta = con.execute(sql, {
            'solicitacao_id': sid, 'status': 'EM_ANDAMENTO',
            'agora': datetime.now(timezone.utc).isoformat(),
        })
        assert resposta.rowcount == 0
        assert con.execute('SELECT retirado_por FROM solicitacoes_exame WHERE id=?', (sid,)).fetchone() == ('ana.recepcao',)
