import asyncio
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.main import app
from src.models.dashboard import (DashboardResumoResponse,OrigemDados,ResumoOperacional,)
from src.providers.implementations.dashboard_demo_provider import (DashboardDemoProvider,)
from src.routers.dashboard import get_dashboard_provider

#! verifica implementação do provider
@pytest.mark.asyncio
async def test_provider_retorna_dados_demonstrativos():
    provider = DashboardDemoProvider()

    resultado = await provider.obter_resumo()

    assert isinstance(resultado, DashboardResumoResponse)
    assert resultado.origem_dados == OrigemDados.DEMONSTRACAO
    assert resultado.operacional.total_casos == 120
    assert resultado.operacional.casos_pendentes == 38

def test_modelo_rejeita_valores_invalidos():
    with pytest.raises(ValidationError):
        ResumoOperacional(casos_atrasados=-1)

#! verifica a proteção de rota
def test_endpoint_exige_autenticacao():
    with TestClient(app) as client:
        resposta = client.get("/api/dashboard/resumo")
    assert resposta.status_code == 401

#! testa resposta HTTP sem credenciais válidas
def test_endpoint_retorna_resumo_autenticado():
    from src.auth.auth import auth_handler

    app.dependency_overrides[auth_handler.decode_token] = lambda: {"sub": "usuario_teste"} #* recurso da API pra testar endpoints isoladamente 

    try:
        with TestClient(app) as client:
            resposta = client.get("/api/dashboard/resumo")

        assert resposta.status_code == 200
        dados = resposta.json()
        assert dados["origem_dados"] == "demonstracao"
        assert dados["operacional"]["total_casos"] == 120
        assert dados["gerencial"]["percentual_cumprimento_prazo"] == 87.5
        
    finally:
        app.dependency_overrides.clear()