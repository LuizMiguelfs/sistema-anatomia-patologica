"""Importação do CSV da ``vw_solicitacao`` do AGHU (provider CSV, somente leitura).

Usa ``tests/fixtures/aghu_vw_solicitacao_anonimizada.csv``: dados FICTÍCIOS no mesmo leiaute do
CSV autorizado (17 colunas, uma linha por amostra, campos com quebra de linha e caracteres
invisíveis). Cobre agrupamento por solicitação, tipo, origem, status, datas, ID de cada amostra,
múltiplas amostras e tipos conflitantes, do helper até a API.
"""
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from src.auth.auth import auth_handler
from src.config import Settings
from src.controllers import solicitacao_controller
from src.dependencies import get_aghu_solicitacao_provider
from src.helpers import aghu_csv_helper as h
from src.main import app
from src.providers.implementations.aghu_solicitacao_csv_provider import AghuSolicitacaoCsvProvider

FIXTURE = Path(__file__).parent / "fixtures" / "aghu_vw_solicitacao_anonimizada.csv"


@pytest.fixture
def aghu() -> AghuSolicitacaoCsvProvider:
    """Provider CSV sobre a amostra anonimizada."""
    return AghuSolicitacaoCsvProvider(str(FIXTURE))


# --- Helper: normalização e IDs ---------------------------------------------
def test_limpar_tira_invisiveis_e_espacos_repetidos():
    assert h.limpar("UAP: HISTOPATOLÓGICO​") == "UAP: HISTOPATOLÓGICO"
    assert h.limpar("9º  SUL ") == "9º SUL"
    assert h.limpar("  ​ ") is None and h.limpar(None) is None


def test_data_iso_converte_formato_do_aghu_e_recusa_data_invalida():
    assert h.data_iso("06/08/2026") == "2026-08-06"
    assert h.data_iso("32/13/2026") is None and h.data_iso("") is None


def test_id_e_rotulo_da_amostra():
    assert h.id_amostra_aghu(800002, 2) == "800002-2"
    assert h.rotulo_amostra("HP-0001/26", 2) == "HP-0001/26-A2"
    amostras = h.identificar_amostras(
        {"solicitacao_aghu": "800002", "identificador_interno": "HP-0001/26"},
        [{"amostra_aghu": "1"}, {"amostra_aghu": "3"}],
    )
    assert [(a["id_aghu"], a["identificador"]) for a in amostras] == [
        ("800002-1", "HP-0001/26-A1"), ("800002-3", "HP-0001/26-A3"),
    ]


def test_colunas_ausentes_confere_o_leiaute():
    assert h.colunas_ausentes(h.COLUNAS_OBRIGATORIAS) == []
    assert h.colunas_ausentes(["codigo_solicitacao", "numero_amostra"])[0] == "cod_status_item"


# --- Agrupamento, tipo, origem, status e datas ------------------------------
@pytest.mark.asyncio
async def test_solicitacao_simples_com_origem_status_e_data(aghu):
    cab = await aghu.buscar_solicitacao("800001")
    assert cab["tipo_exame"] == "HP" and cab["tipos_exame"] == ["HP"] and cab["pendencias"] == []
    assert cab["origem"] == "Internação" and cab["unidade"] == "9º SUL" and cab["especialidade"] == "CIRURGIA GERAL"
    assert cab["status_aghu"] == "LI" and cab["status_descricao"] == "LIBERADO"
    assert cab["data_solicitacao"] == "2026-03-10" and cab["convenio"] == "SUS"
    assert cab["paciente_nome"] == "A.F." and cab["prontuario_aghu"] == "90000001"
    assert cab["paciente_codigo_aghu"] is None  # a view não traz o código do paciente
    assert cab["urgente"] is False and cab["qtd_amostras"] == 1
    # Minimização (LGPD): o SAP não precisa de data de nascimento nem de informação clínica.
    assert "data_nascimento" not in cab and "informacoes_clinica" not in cab


@pytest.mark.asyncio
async def test_multiplas_amostras_do_mesmo_tipo_com_siglas_diferentes(aghu):
    cab = await aghu.buscar_solicitacao("800002")
    amostras = await aghu.listar_amostras("800002")
    assert cab["tipo_exame"] == "HP" and cab["pendencias"] == []  # MBIOP + MPCIR + APECR são todos HP
    assert [a["id_amostra"] for a in amostras] == ["800002-1", "800002-2", "800002-3"]
    assert [(a["codigo_exame"], a["descricao"]) for a in amostras] == [
        ("MBIOP", "MAMA DIREITA"), ("MPCIR", "SEGMENTO DE MAMA ESQUERDA"), ("APECR", "LINFONODO"),
    ]
    assert len({a["id_amostra"] for a in amostras}) == 3  # cada amostra se diferencia das outras
    assert cab["status_aghu"] == h.STATUS_MISTO  # LIBERADO e EXECUTANDO
    assert {a["status"] for a in amostras} == {"LI", "EX"}


@pytest.mark.asyncio
async def test_numeracao_do_aghu_e_mantida_mesmo_nao_continua(aghu):
    amostras = await aghu.listar_amostras("800003")
    assert [a["amostra_aghu"] for a in amostras] == [4, 5]  # ordenadas, sem renumerar
    assert [a["id_amostra"] for a in amostras] == ["800003-4", "800003-5"]
    assert (await aghu.buscar_solicitacao("800003"))["tipo_exame"] == "CCV"


@pytest.mark.asyncio
async def test_tipos_conflitantes_ficam_sem_tipo(aghu):
    cab = await aghu.buscar_solicitacao("800004")  # peça cirúrgica + congelação na mesma solicitação
    assert cab["tipo_exame"] is None and cab["tipos_exame"] == ["CO", "HP"]
    assert cab["pendencias"] == [h.PENDENCIA_TIPOS_CONFLITANTES]
    assert len(await aghu.listar_amostras("800004")) == 2
    ihq = await aghu.buscar_solicitacao("800013")  # IHQ + mama
    assert ihq["tipo_exame"] is None and ihq["tipos_exame"] == ["HP", "IHQ"]


@pytest.mark.asyncio
async def test_amostra_cancelada_nao_conta_para_o_tipo_nem_para_abertura(aghu):
    cab = await aghu.buscar_solicitacao("800005")  # HP liberado + IHQ cancelada
    assert cab["tipo_exame"] == "HP" and cab["pendencias"] == []
    assert cab["qtd_amostras"] == 1 and cab["amostras_canceladas"] == 1
    assert [a["id_amostra"] for a in await aghu.listar_amostras("800005")] == ["800005-1"]

    todas = await aghu.buscar_solicitacao("800006")
    assert todas["tipo_exame"] is None and todas["pendencias"] == [h.PENDENCIA_SEM_AMOSTRA_VIGENTE]
    assert todas["status_aghu"] == "CA" and await aghu.listar_amostras("800006") == []


@pytest.mark.asyncio
async def test_paciente_externo_sem_prontuario(aghu):
    cab = await aghu.buscar_solicitacao("800007")
    assert cab["origem"] == "Paciente Externo" and cab["prontuario_aghu"] is None
    assert cab["especialidade"] is None and cab["unidade"] == "UAP: HISTOPATOLÓGICO"
    assert cab["tipo_exame"] == "CG" and cab["status_aghu"] == "AC"


@pytest.mark.asyncio
async def test_congelacao_e_urgente(aghu):
    cab = await aghu.buscar_solicitacao("800008")
    assert cab["tipo_exame"] == "CO" and cab["urgente"] is True


@pytest.mark.asyncio
async def test_pendencias_de_sigla_duplicidade_e_paciente(aghu):
    assert (await aghu.buscar_solicitacao("800009"))["pendencias"] == [h.PENDENCIA_SIGLA_NAO_MAPEADA]
    duplicada = await aghu.buscar_solicitacao("800011")
    assert duplicada["pendencias"] == [h.PENDENCIA_AMOSTRA_DUPLICADA] and duplicada["tipo_exame"] is None
    assert [a["descricao"] for a in await aghu.listar_amostras("800011")] == ["ESÔFAGO DISTAL"]  # não sobrescreve
    divergente = await aghu.buscar_solicitacao("800012")
    assert divergente["pendencias"] == [h.PENDENCIA_PACIENTE_DIVERGENTE] and divergente["tipo_exame"] is None


@pytest.mark.asyncio
async def test_linhas_fora_da_anatomia_invalidas_e_data_ruim(aghu):
    assert await aghu.buscar_solicitacao("800010") is None  # só tem exame de outro laboratório
    assert await aghu.buscar_solicitacao("999999") is None
    cito = await aghu.buscar_solicitacao("800014")
    assert cito["data_solicitacao"] is None and cito["tipo_exame"] == "CG"
    assert (await aghu.listar_amostras("800014"))[0]["descricao"] is None
    resumo = await aghu.resumo()
    assert resumo["linhas_invalidas"] == 1 and resumo["linhas_fora_da_anatomia"] == 1
    assert resumo["solicitacoes"] == 13 and "800010" not in await aghu.listar_numeros()
    assert resumo["por_pendencia"][h.PENDENCIA_TIPOS_CONFLITANTES] == 2


@pytest.mark.asyncio
async def test_numero_com_zeros_a_esquerda(aghu):
    assert (await aghu.buscar_solicitacao("0800001"))["solicitacao_aghu"] == 800001


# --- Arquivo: leiaute, ausência e releitura ---------------------------------
@pytest.mark.asyncio
async def test_leiaute_errado_ou_arquivo_ausente_falham_sem_expor_dados(tmp_path):
    errado = tmp_path / "errado.csv"
    errado.write_text('"codigo_solicitacao","nome_paciente"\n"1","FULANO"\n', encoding="utf-8")
    with pytest.raises(RuntimeError) as erro:
        await AghuSolicitacaoCsvProvider(str(errado)).buscar_solicitacao("1")
    assert "numero_amostra" in str(erro.value) and "FULANO" not in str(erro.value)
    with pytest.raises(RuntimeError):
        await AghuSolicitacaoCsvProvider(str(tmp_path / "nao_existe.csv")).buscar_solicitacao("1")


@pytest.mark.asyncio
async def test_aceita_bom_e_relê_o_arquivo_quando_ele_muda(tmp_path):
    copia = tmp_path / "vw.csv"
    copia.write_bytes(b"\xef\xbb\xbf" + FIXTURE.read_bytes())
    aghu = AghuSolicitacaoCsvProvider(str(copia))
    assert await aghu.buscar_solicitacao("800001") is not None
    linhas = FIXTURE.read_text(encoding="utf-8").splitlines(keepends=True)
    copia.write_text(linhas[0] + "".join(l for l in linhas[1:] if not l.startswith('"800001"') and "Linha 2" not in l),
                     encoding="utf-8")
    assert await aghu.buscar_solicitacao("800001") is None


# --- Configuração ------------------------------------------------------------
def test_config_aceita_csv_fora_de_producao_e_recusa_em_producao(monkeypatch):
    monkeypatch.setattr(Settings, "AGHU_PROVIDER_TYPE", "CSV")
    Settings.validate_config()
    monkeypatch.setattr(Settings, "ENV", "production")
    with pytest.raises(RuntimeError, match="AGHU_PROVIDER_TYPE=POSTGRES"):
        Settings.validate_config()


# --- API: abertura a partir do CSV -------------------------------------------
def _h(username: str, role: str) -> Dict[str, str]:
    """Cabeçalho com token de acesso."""
    token = auth_handler.create_access_token({"username": username, "role": role, "groups": ["Users"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Banco migrado (Alembic), Recepção cadastrada e AGHU lido da amostra anonimizada."""
    db = tmp_path / "app.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db}")
    command.upgrade(Config("alembic.ini"), "head")
    monkeypatch.setattr(solicitacao_controller, "_ano_local", lambda: 2026)
    csv = tmp_path / "vw_solicitacao.csv"
    shutil.copy(FIXTURE, csv)
    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: AghuSolicitacaoCsvProvider(str(csv))
    try:
        with TestClient(app) as client:
            with sqlite3.connect(db) as conn:
                conn.execute("INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, 1, ?)",
                             ("ana.recepcao", "RECEPCAO", datetime.now(timezone.utc).isoformat()))
            yield client, db
    finally:
        app.dependency_overrides.pop(get_aghu_solicitacao_provider, None)


def test_api_abre_solicitacao_com_varias_amostras_identificadas(api):
    client, db = api
    rec = _h("ana.recepcao", "RECEPCAO")
    previa = client.get("/api/solicitacoes/aghu/solicitacao/800002", headers=rec)
    assert previa.status_code == 200, previa.text
    assert previa.json()["origem"] == "Ambulatório" and previa.json()["data_solicitacao"] == "2026-03-11"
    assert [a["id_amostra"] for a in previa.json()["amostras"]] == ["800002-1", "800002-2", "800002-3"]

    r = client.post("/api/solicitacoes", json={"solicitacao_aghu": "800002"}, headers=rec)
    assert r.status_code == 201, r.text
    amostras = r.json()["amostras"]
    assert [a["identificador"] for a in amostras] == ["HP-0001/26-A1", "HP-0001/26-A2", "HP-0001/26-A3"]
    assert [a["id_aghu"] for a in amostras] == ["800002-1", "800002-2", "800002-3"]
    assert [a["descricao"] for a in amostras] == ["MAMA DIREITA", "SEGMENTO DE MAMA ESQUERDA", "LINFONODO"]
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT paciente_codigo_aghu FROM solicitacoes_exame").fetchone() == ("",)

    # Só as vigentes entram; a numeração do AGHU é preservada no rótulo.
    r = client.post("/api/solicitacoes", json={"solicitacao_aghu": "800003"}, headers=rec)
    assert [a["identificador"] for a in r.json()["amostras"]] == ["CCV-0001/26-A4", "CCV-0001/26-A5"]

    # A conferência com o AGHU funciona mesmo sem o código do paciente na view.
    conferencia = client.get(f"/api/solicitacoes/{r.json()['id']}/conferencia-aghu", headers=rec)
    assert conferencia.status_code == 200, conferencia.text
    assert conferencia.json()["divergencias"] == {}


def test_api_bloqueia_tipos_conflitantes_sem_gravar_nada(api):
    client, db = api
    rec = _h("ana.recepcao", "RECEPCAO")
    previa = client.get("/api/solicitacoes/aghu/solicitacao/800004", headers=rec).json()
    assert previa["tipo_exame"] is None and previa["pendencias"] == ["TIPOS_CONFLITANTES"]

    r = client.post("/api/solicitacoes", json={"solicitacao_aghu": "800004"}, headers=rec)
    assert r.status_code == 409
    assert "tipos de exame diferentes" in r.json()["detail"] and "(CO, HP)" in r.json()["detail"]
    assert client.post("/api/solicitacoes", json={"solicitacao_aghu": "800006"}, headers=rec).status_code == 409
    assert client.post("/api/solicitacoes", json={"solicitacao_aghu": "800010"}, headers=rec).status_code == 404
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM solicitacoes_exame").fetchone() == (0,)
        assert conn.execute("SELECT COUNT(*) FROM solicitacao_amostras").fetchone() == (0,)
