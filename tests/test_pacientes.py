# tests/test_pacientes.py
"""
Testes do módulo de Pacientes (CRUD + buscas) pela API, usando o provedor CSV
sobre uma CÓPIA temporária de data/pacientes.csv e um banco de auditoria temporário.
O arquivo real data/pacientes.csv e o data/app.db nunca são alterados.
"""

import json
import shutil
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.dependencies import get_paciente_provider
from src.main import app
from src.models.audit_log import AuditLog
from src.providers.implementations.paciente_csv_provider import PacienteCsvProvider
from src.providers.implementations.paciente_postgres_provider import PacientePostgresProvider
from src.routers.paciente import STRATEGY

CSV_ORIGINAL = Path(__file__).resolve().parent.parent / "data" / "pacientes.csv"
CPF_VALIDO = "529.982.247-25"
CPF_VALIDO_2 = "111.444.777-35"
CNS_VALIDO = "700000000000005"


def _cadastrar_admin_de_teste(db_path: Path) -> None:
    """Libera o admin APENAS no banco temporario desta fixture."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO authorized_users (username, role, active, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("admin", "CHEFIA", 1, datetime.now(timezone.utc).isoformat()),
        )


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """TestClient com CSV e banco de auditoria isolados em diretório temporário."""
    csv_tmp = tmp_path / "pacientes.csv"
    shutil.copy(CSV_ORIGINAL, csv_tmp)
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")

    dependencia = get_paciente_provider(STRATEGY)
    app.dependency_overrides[dependencia] = lambda: PacienteCsvProvider(csv_path=str(csv_tmp))
    try:
        with TestClient(app) as client:
            _cadastrar_admin_de_teste(tmp_path / "app.db")
            token = client.post("/api/login", data={"username": "admin", "password": "admin"}).json()["access_token"]
            client.headers.update({"Authorization": f"Bearer {token}"})
            yield client, csv_tmp
    finally:
        app.dependency_overrides.pop(dependencia, None)


def _auditorias(client: TestClient):
    """
    Lê os registros de auditoria de negócio do banco temporário.
    Ignora os eventos de SEGURANCA (ex.: o LOGIN feito pela fixture), que não são deste módulo.
    """
    async def _consulta():
        async with client.app.state.app_db.async_session_maker() as session:
            result = await session.execute(
                select(AuditLog).where(AuditLog.categoria == "NEGOCIO_CLINICO").order_by(AuditLog.id)
            )
            return list(result.scalars().all())
    return client.portal.call(_consulta)


def _novo_paciente(**extra):
    """Payload válido de cadastro."""
    base = {
        "nome": "  maria   da silva ",
        "dt_nascimento": "1990-05-20",
        "sexo": "f",
        "cor": "parda",
        "nome_mae": "ana da silva",
        "cpf": CPF_VALIDO,
        "cns": CNS_VALIDO,
    }
    base.update(extra)
    return base


# ------------------------------------------------------------------ segurança
def test_rotas_exigem_autenticacao():
    """Default-Private: sem token, todas as rotas respondem 401."""
    with TestClient(app) as client:
        assert client.get("/api/pacientes").status_code == 401
        assert client.post("/api/pacientes", json=_novo_paciente()).status_code == 401
        assert client.delete("/api/pacientes/1").status_code == 401


# --------------------------------------------------------------- leitura/busca
def test_capacidades_csv(ambiente):
    client, _ = ambiente
    assert client.get("/api/pacientes/capacidades").json() == {"fonte": "CSV", "escrita": True, "exclusao": True}


def test_listar_ordenado_e_paginado(ambiente):
    client, _ = ambiente
    todos = client.get("/api/pacientes").json()
    assert len(todos) == 4
    assert [p["nome"] for p in todos] == sorted(p["nome"] for p in todos)
    assert todos[0]["dt_nascimento"] and "especialidade" not in todos[0]

    pagina = client.get("/api/pacientes", params={"limite": 2, "offset": 2}).json()
    assert [p["codigo"] for p in pagina] == [p["codigo"] for p in todos[2:4]]


def test_null_do_csv_vira_none(ambiente):
    client, _ = ambiente
    bruno = client.get("/api/pacientes/77002").json()
    assert bruno["cpf"] is None and bruno["nome"].startswith("BRUNO")


def test_busca_por_nome_sem_acento_e_case_insensitive(ambiente):
    client, _ = ambiente
    r = client.get("/api/pacientes", params={"termo": "fernánda"}).json()
    assert [p["codigo"] for p in r] == [77003]


def test_busca_por_codigo_e_cpf(ambiente):
    client, _ = ambiente
    assert [p["nome"] for p in client.get("/api/pacientes", params={"termo": "77004"}).json()] == ["LUCAS ALMEIDA (CSV)"]
    assert [p["codigo"] for p in client.get("/api/pacientes", params={"termo": "333.333.333-33"}).json()] == [77003]


def test_busca_por_nome_curta_retorna_400(ambiente):
    client, _ = ambiente
    r = client.get("/api/pacientes", params={"termo": "ab"})
    assert r.status_code == 400 and "3 caracteres" in r.json()["detail"]


def test_obter_inexistente_404(ambiente):
    client, _ = ambiente
    r = client.get("/api/pacientes/999999")
    assert r.status_code == 404 and r.json() == {"detail": "Paciente não encontrado."}


def test_limite_invalido_400(ambiente):
    client, _ = ambiente
    r = client.get("/api/pacientes", params={"limite": 1000})
    assert r.status_code == 400 and "detail" in r.json()


# ------------------------------------------------------------------- escrita
def test_criar_normaliza_persiste_e_audita(ambiente):
    client, csv_tmp = ambiente
    r = client.post("/api/pacientes", json=_novo_paciente())
    assert r.status_code == 201, r.text
    criado = r.json()
    assert criado["codigo"] == 10000017  # maior código + 1
    assert criado["nome"] == "MARIA DA SILVA"
    assert criado["nome_mae"] == "ANA DA SILVA"
    assert (criado["sexo"], criado["cor"], criado["cpf"]) == ("F", "PARDA", CPF_VALIDO)

    assert client.get(f"/api/pacientes/{criado['codigo']}").json() == criado
    assert "MARIA DA SILVA" in csv_tmp.read_text(encoding="utf-8")

    logs = _auditorias(client)
    assert len(logs) == 1
    log = logs[0]
    assert (log.usuario, log.categoria, log.acao, log.recurso) == ("admin", "NEGOCIO_CLINICO", "CRIAR_PACIENTE", "paciente:10000017")
    assert log.dados_anteriores is None
    assert json.loads(log.dados_novos)["nome"] == "MARIA DA SILVA"
    assert log.ip_origem


@pytest.mark.parametrize(
    "extra, trecho",
    [
        ({"cpf": "123.456.789-00"}, "CPF inválido"),
        ({"cns": "123456789012345"}, "CNS"),
        ({"dt_nascimento": (date.today() + timedelta(days=1)).isoformat()}, "futuro"),
        ({"dt_nascimento": "1899-12-31"}, "1900"),
        ({"nome": "ab"}, "nome"),
        ({"sexo": "X"}, "sexo"),
        ({"cor": "AZUL"}, "cor"),
    ],
)
def test_criar_validacoes_400(ambiente, extra, trecho):
    client, _ = ambiente
    r = client.post("/api/pacientes", json=_novo_paciente(**extra))
    assert r.status_code == 400, r.text
    assert trecho.lower() in r.json()["detail"].lower()
    assert _auditorias(client) == []


def test_criar_cpf_duplicado_409(ambiente):
    client, _ = ambiente
    assert client.post("/api/pacientes", json=_novo_paciente()).status_code == 201
    r = client.post("/api/pacientes", json=_novo_paciente(nome="Outra Pessoa", cpf="52998224725"))
    assert r.status_code == 409


def test_criar_sem_campos_opcionais(ambiente):
    client, _ = ambiente
    r = client.post("/api/pacientes", json={"nome": "Jose Teste", "dt_nascimento": "2000-01-01", "sexo": "M", "cpf": "", "cns": ""})
    assert r.status_code == 201, r.text
    assert r.json()["cpf"] is None and r.json()["cor"] is None


def test_atualizar_audita_antes_e_depois(ambiente):
    client, _ = ambiente
    original = client.get("/api/pacientes/77002").json()
    payload = {**_novo_paciente(nome="Bruno Lima Atualizado", cpf=CPF_VALIDO_2), "sexo": "M"}
    r = client.put("/api/pacientes/77002", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == "BRUNO LIMA ATUALIZADO" and r.json()["cpf"] == CPF_VALIDO_2

    log = _auditorias(client)[-1]
    assert log.acao == "ALTERAR_PACIENTE" and log.recurso == "paciente:77002"
    assert json.loads(log.dados_anteriores)["nome"] == original["nome"]
    assert json.loads(log.dados_novos)["nome"] == "BRUNO LIMA ATUALIZADO"


def test_atualizar_mantendo_proprio_cpf_nao_conflita(ambiente):
    client, _ = ambiente
    criado = client.post("/api/pacientes", json=_novo_paciente()).json()
    r = client.put(f"/api/pacientes/{criado['codigo']}", json=_novo_paciente(nome="Maria Editada"))
    assert r.status_code == 200, r.text


def test_atualizar_inexistente_404(ambiente):
    client, _ = ambiente
    assert client.put("/api/pacientes/999999", json=_novo_paciente()).status_code == 404


def test_excluir_e_logico_e_auditado(ambiente):
    client, csv_tmp = ambiente
    assert client.delete("/api/pacientes/77004").status_code == 204

    assert client.get("/api/pacientes/77004").status_code == 404
    assert 77004 not in [p["codigo"] for p in client.get("/api/pacientes").json()]
    assert client.delete("/api/pacientes/77004").status_code == 404

    # Soft delete: a linha continua no arquivo, com deleted_at preenchido
    linha = next(l for l in csv_tmp.read_text(encoding="utf-8").splitlines() if l.startswith("77004,"))
    assert "LUCAS ALMEIDA" in linha and linha.rstrip().split(",")[-1] != ""

    log = _auditorias(client)[-1]
    assert log.acao == "EXCLUIR_PACIENTE"
    assert json.loads(log.dados_anteriores)["codigo"] == 77004


def test_codigo_nao_e_reutilizado_apos_exclusao(ambiente):
    client, _ = ambiente
    criado = client.post("/api/pacientes", json=_novo_paciente()).json()
    client.delete(f"/api/pacientes/{criado['codigo']}")
    novo = client.post("/api/pacientes", json=_novo_paciente()).json()
    assert novo["codigo"] == criado["codigo"] + 1


def test_colunas_extras_do_csv_sao_preservadas(ambiente):
    client, csv_tmp = ambiente
    client.post("/api/pacientes", json=_novo_paciente())
    cabecalho = csv_tmp.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert {"especialidade", "procedimento", "deleted_at", "cns"} <= set(cabecalho)
    assert "Biópsia de pele" in csv_tmp.read_text(encoding="utf-8")


# ------------------------------------------------- AGHU (Postgres) somente leitura
@pytest.fixture
def ambiente_aghu_somente_leitura(tmp_path, monkeypatch):
    """Provedor Postgres com escrita desabilitada; nenhuma query de escrita pode chegar ao banco."""
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")
    dependencia = get_paciente_provider(STRATEGY)
    app.dependency_overrides[dependencia] = lambda: PacientePostgresProvider(session=None, escrita_habilitada=False)
    try:
        with TestClient(app) as client:
            _cadastrar_admin_de_teste(tmp_path / "app.db")
            token = client.post("/api/login", data={"username": "admin", "password": "admin"}).json()["access_token"]
            client.headers.update({"Authorization": f"Bearer {token}"})
            yield client
    finally:
        app.dependency_overrides.pop(dependencia, None)


def test_aghu_bloqueia_escrita_e_exclusao(ambiente_aghu_somente_leitura):
    client = ambiente_aghu_somente_leitura
    assert client.get("/api/pacientes/capacidades").json() == {"fonte": "POSTGRES", "escrita": False, "exclusao": False}

    r = client.post("/api/pacientes", json=_novo_paciente())
    assert r.status_code == 403 and "somente leitura" in r.json()["detail"]
    assert client.put("/api/pacientes/1", json=_novo_paciente()).status_code == 403
    assert client.delete("/api/pacientes/1").status_code == 403
    assert _auditorias(client) == []
