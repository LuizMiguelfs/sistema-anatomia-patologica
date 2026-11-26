"""Retrato das filas no Início (T5.1): os números do painel batem com as filas das telas."""
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from src.auth.auth import auth_handler
from src.controllers import solicitacao_controller
from src.dependencies import get_aghu_solicitacao_provider
from src.helpers.formularios_fase import FASES
from src.main import app
from src.providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface

TIPOS = {"101": "HP", "102": "CO", "103": "HP", "104": "RL", "105": "HP"}
NOME = "PACIENTE FICTICIO DO PAINEL"


class AghuFalso(AghuSolicitacaoProviderInterface):
    """AGHU simulado com cinco solicitações (CO é sempre urgente)."""

    async def buscar_solicitacao(self, numero: str) -> Optional[Dict[str, Any]]:
        """Cabeçalho fictício."""
        tipo = TIPOS.get(numero)
        return {"solicitacao_aghu": int(numero), "paciente_codigo_aghu": 1, "tipo_exame": tipo,
                "prontuario_aghu": f"9{numero}", "paciente_nome": NOME} if tipo else None

    async def listar_amostras(self, numero: str) -> List[Dict[str, Any]]:
        """Uma amostra."""
        return [{"amostra_aghu": 1, "descricao": "Amostra fictícia"}]


def _h(username: str, role: str) -> Dict[str, str]:
    token = auth_handler.create_access_token({"username": username, "role": role, "groups": ["Users"]})
    return {"Authorization": f"Bearer {token}"}


REC, RES, PAT = _h("ana.recepcao", "RECEPCAO"), _h("caio.res", "RESIDENTE"), _h("dora.pat", "PRECEPTORIA")
LAB = _h("bia.lab", "LABORATORIO")


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Banco migrado, usuários, AGHU simulado e as cinco solicitações abertas."""
    db = tmp_path / "app.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db}")
    command.upgrade(Config("alembic.ini"), "head")
    monkeypatch.setattr(solicitacao_controller, "_ano_local", lambda: 2026)
    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: AghuFalso()
    try:
        with TestClient(app) as client:
            with sqlite3.connect(db) as conn:
                for user, role in (("ana.recepcao", "RECEPCAO"), ("caio.res", "RESIDENTE"), ("dora.pat", "PRECEPTORIA"),
                                   ("bia.lab", "LABORATORIO")):
                    conn.execute("INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, 1, ?)",
                                 (user, role, datetime.now(timezone.utc).isoformat()))
            ids = {}
            for numero in TIPOS:
                r = client.post("/api/solicitacoes", json={"solicitacao_aghu": numero}, headers=REC)
                assert r.status_code == 201, r.text
                ids[numero] = r.json()["id"]
            yield client, ids
    finally:
        app.dependency_overrides.pop(get_aghu_solicitacao_provider, None)


def _filas(client) -> Dict[str, Any]:
    r = client.get("/api/dashboard/resumo", headers=PAT)
    assert r.status_code == 200, r.text
    return r.json()["filas"]


def _por_etapa(filas) -> Dict[str, Dict[str, Any]]:
    return {f["etapa"]: f for f in filas["fases"]}


def _confere_com_as_telas(client, filas) -> None:
    """Cada número do painel é o mesmo que a tela correspondente mostra."""
    nao_retiradas = client.get("/api/solicitacoes", params={"situacao": "NAO_RETIRADO"}, headers=REC).json()
    assert filas["nao_retiradas"] == nao_retiradas["total"]
    for fase in filas["fases"]:
        fila = client.get(f"/api/fases/{fase['etapa']}/fila", headers=PAT).json()["items"]
        pendentes = [i for i in fila if i["pendente"]]
        assert fase["pendentes"] == len(pendentes), fase["etapa"]
        assert fase["urgentes"] == len([i for i in pendentes if i["urgente"]]), fase["etapa"]


def test_retrato_bate_com_as_filas_e_conta_quem_aguarda_o_patologista(api):
    client, ids = api
    for numero in ("101", "102", "104"):  # HP → Macroscopia, CO → Congelação (urgente), RL → Revisão
        assert client.post(f"/api/solicitacoes/{ids[numero]}/retirar", json={"username": "ana.recepcao", "password": "admin"}, headers=REC).status_code == 200

    # Congelação: o residente salva a análise preliminar (o pré-laudo dessa fase) → aguarda o patologista.
    r = client.put(f"/api/fases/CONGELACAO/solicitacoes/{ids['102']}",
                   json={"dados": {"analise_preliminar": "Texto fictício"}}, headers=RES)
    assert r.status_code == 200, r.text
    # Revisão: só observações, sem pré-laudo → ainda não aguarda o patologista.
    r = client.put(f"/api/fases/REVISAO/solicitacoes/{ids['104']}",
                   json={"dados": {"observacoes": "Separar lâminas"}}, headers=RES)
    assert r.status_code == 200, r.text

    filas = _filas(client)
    fases = _por_etapa(filas)
    assert [f["etapa"] for f in filas["fases"]] == [f["etapa"] for f in FASES]  # ordem do menu
    assert filas["nao_retiradas"] == 2 and filas["nao_retiradas_urgentes"] == 0
    assert filas["urgentes"] == 1 and fases["CONGELACAO"]["urgentes"] == 1
    assert fases["MACROSCOPIA"]["pendentes"] == 1 and fases["CONGELACAO"]["pendentes"] == 1
    assert fases["REVISAO"]["pendentes"] == 1 and fases["MICROSCOPIA"]["pendentes"] == 0
    assert filas["aguardando_patologista"] == 1
    assert fases["CONGELACAO"]["aguardando_patologista"] == 1 and fases["REVISAO"]["aguardando_patologista"] == 0
    assert fases["MACROSCOPIA"]["aguardando_patologista"] is None  # fase sem validação do patologista
    _confere_com_as_telas(client, filas)

    # O residente salva o pré-laudo da Revisão: agora são dois aguardando o patologista.
    r = client.put(f"/api/fases/REVISAO/solicitacoes/{ids['104']}",
                   json={"dados": {"pre_laudo": "Pré-laudo fictício"}}, headers=RES)
    assert r.status_code == 200, r.text
    assert _filas(client)["aguardando_patologista"] == 2

    # O patologista valida e conclui a Revisão: sai da fila e do "aguardando".
    r = client.post(f"/api/fases/REVISAO/solicitacoes/{ids['104']}/concluir",
                    json={"dados": {"qtd_laminas": 2, "diagnostico": "Diagnóstico fictício"}}, headers=PAT)
    assert r.status_code == 200, r.text
    filas = _filas(client)
    assert _por_etapa(filas)["REVISAO"]["pendentes"] == 0 and filas["aguardando_patologista"] == 1
    _confere_com_as_telas(client, filas)


def test_retrato_nao_traz_dados_de_paciente(api):
    client, ids = api
    corpo = client.get("/api/dashboard/resumo", headers=REC).text
    assert NOME not in corpo and "9101" not in corpo
    assert _filas(client)["nao_retiradas"] == 5


def test_indicadores_contam_so_o_que_o_fluxo_registra(api):
    """T5.2: "aguardando complementação" = encaminhadas que ainda não voltaram; inconformidade
    (que o SAP ainda não registra) fica "Não medido" em vez de zero."""
    client, ids = api
    sid = ids["101"]  # HP
    assert client.post(f"/api/solicitacoes/{sid}/retirar", json={"username": "ana.recepcao", "password": "admin"}, headers=REC).status_code == 200
    macro = {"descricao_macroscopica": "x", "qtd_fragmentos": 1, "qtd_cassetes": 1, "laudo_macroscopico": "x"}
    assert client.post(f"/api/fases/MACROSCOPIA/solicitacoes/{sid}/concluir", json={"dados": macro}, headers=RES).status_code == 200
    proc = {"inicio": "Histotécnico", "qtd_blocos": 1, "qtd_laminas": 2}
    assert client.post(f"/api/fases/PROCESSAMENTO/solicitacoes/{sid}/concluir", json={"dados": proc}, headers=LAB).status_code == 200

    def resumo():
        r = client.get("/api/dashboard/resumo", headers=PAT)
        assert r.status_code == 200, r.text
        return r.json()

    assert resumo()["operacional"]["aguardando_complementacao"] == 0
    # Na Microscopia, o patologista pede IHQ: a solicitação fica aguardando o processamento complementar.
    r = client.post(f"/api/solicitacoes/{sid}/encaminhar", json={"destino": "IHQ", "motivo": "Painel de IHQ"}, headers=PAT)
    assert r.status_code == 200, r.text
    dados = resumo()
    assert dados["operacional"]["aguardando_complementacao"] == 1
    assert {f["etapa"]: f for f in dados["filas"]["fases"]}["IHQ"]["pendentes"] == 1

    # O laboratório conclui a IHQ: a solicitação volta à Microscopia e deixa de aguardar.
    ihq = {"marcadores": "CK7", "qtd_laminas": 1, "resultado": "Resultado fictício"}
    r = client.post(f"/api/fases/IHQ/solicitacoes/{sid}/concluir", json={"dados": ihq}, headers=LAB)
    assert r.status_code == 200, r.text
    dados = resumo()
    assert dados["operacional"]["aguardando_complementacao"] == 0
    assert {f["etapa"]: f for f in dados["filas"]["fases"]}["MICROSCOPIA"]["pendentes"] == 1

    # O que o fluxo não registra continua "Não medido" (null), nunca zero.
    gerencial = dados["gerencial"]
    assert all(valor is None for valor in gerencial.values()), gerencial
    assert "Não mensurado" in dados["criterios"]["total_inconsistencias"]
