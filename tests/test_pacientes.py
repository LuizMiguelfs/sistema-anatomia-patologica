"""Módulo de consulta de pacientes: o SAP não cadastra, edita ou exclui pacientes."""
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.auth.auth import auth_handler
from src.dependencies import get_paciente_provider
from src.providers.implementations.paciente_csv_provider import PacienteCsvProvider
from src.routers.paciente import STRATEGY


@pytest.fixture
def api_paciente(tmp_path):
    copia = tmp_path / "pacientes.csv"
    shutil.copyfile(Path(__file__).resolve().parent.parent / "data/pacientes.csv", copia)
    dependencia = get_paciente_provider(STRATEGY)
    app.dependency_overrides[dependencia] = lambda: PacienteCsvProvider(str(copia))
    app.dependency_overrides[auth_handler.decode_token] = lambda: {"sub": "tester", "username": "tester", "role": "RECEPCAO"}
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(dependencia, None)
        app.dependency_overrides.pop(auth_handler.decode_token, None)


def test_catalogo_csv_e_somente_leitura_na_api(api_paciente):
    client = api_paciente
    resp = client.get("/api/pacientes/capacidades")
    assert resp.status_code == 200
    assert resp.json() == {"fonte": "CSV", "escrita": False, "exclusao": False}
    assert client.get("/api/pacientes").status_code == 200


@pytest.mark.parametrize("metodo,rota", [
    ("POST", "/api/pacientes"),
    ("PUT", "/api/pacientes/77002"),
    ("DELETE", "/api/pacientes/77002"),
])
def test_sap_nao_permite_mutacoes_cadastrais(api_paciente, metodo, rota):
    resp = api_paciente.request(metodo, rota, json={"nome": "TESTE"} if metodo != "DELETE" else None)
    assert resp.status_code == 405


def test_paciente_inexistente_e_busca_curta(api_paciente):
    assert api_paciente.get("/api/pacientes/999999999").status_code == 404
    r = api_paciente.get("/api/pacientes", params={"termo": "ab"})
    assert r.status_code == 400 and "3 caracteres" in r.json()["detail"]
