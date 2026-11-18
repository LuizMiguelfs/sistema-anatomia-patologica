import asyncio
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.main import app
from src.models.dashboard import (DashboardResumoResponse,OrigemDados,ResumoOperacional,)
from src.providers.implementations.dashboard_demo_provider import (DashboardDemoProvider,)
from src.dependencies import get_dashboard_provider

#! verifica implementação do provider
@pytest.mark.asyncio
async def test_provider_retorna_dados_demonstrativos():
    provider = DashboardDemoProvider()

    resultado = await provider.obter_resumo()

    assert isinstance(resultado, DashboardResumoResponse)
    assert resultado.origem_dados == OrigemDados.DEMONSTRACAO
    assert resultado.operacional.total_solicitacoes == 120
    assert resultado.operacional.solicitacoes_pendentes == 38

def test_modelo_rejeita_valores_invalidos():
    with pytest.raises(ValidationError):
        ResumoOperacional(solicitacoes_atrasadas=-1)

#! verifica a proteção de rota
def test_endpoint_exige_autenticacao():
    with TestClient(app) as client:
        resposta = client.get("/api/dashboard/resumo")
    assert resposta.status_code == 401

#! testa resposta HTTP sem credenciais válidas
def test_endpoint_retorna_resumo_autenticado():
    from src.auth.auth import auth_handler

    app.dependency_overrides[auth_handler.decode_token] = lambda: {"sub": "usuario_teste"}
    app.dependency_overrides[get_dashboard_provider] = lambda: DashboardDemoProvider() 

    try:
        with TestClient(app) as client:
            resposta = client.get("/api/dashboard/resumo")

        assert resposta.status_code == 200
        dados = resposta.json()
        assert dados["origem_dados"] == "demonstracao"
        assert dados["operacional"]["total_solicitacoes"] == 120
        assert dados["gerencial"]["percentual_cumprimento_prazo"] == 87.5
        
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_sqlite_com_dados_reais_e_sla_explicito(tmp_path):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from src.providers.implementations.dashboard_sqlite_provider import DashboardSqliteProvider

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'dashboard.db'}")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE solicitacoes_exame (
                id INTEGER PRIMARY KEY,
                tipo_exame TEXT, status TEXT, criado_em TEXT, etapa_atual TEXT, ativo INTEGER
            )
        """))
        await conn.execute(text("""
            CREATE TABLE solicitacao_inconformidades (solicitacao_id INTEGER, situacao TEXT)
        """))
        await conn.execute(text("""
            INSERT INTO solicitacoes_exame(tipo_exame, status, criado_em, etapa_atual, ativo)
            VALUES ('HP', 'EM_ANDAMENTO', :criado, 'RECEPCAO', 1)
        """), {"criado": (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()})
    try:
        async with async_sessionmaker(engine)() as sess:
            sem_sla = await DashboardSqliteProvider(sess).obter_resumo()
            assert sem_sla.origem_dados == OrigemDados.BANCO_DADOS
            assert sem_sla.operacional.total_solicitacoes == 1
            assert sem_sla.operacional.solicitacoes_pendentes == 1
            assert sem_sla.operacional.solicitacoes_atrasadas is None
            assert sem_sla.gerencial.tempo_medio_liberacao_horas is None

            com_sla = await DashboardSqliteProvider(sess, {"HP": 4}).obter_resumo()
            assert com_sla.operacional.solicitacoes_atrasadas == 1
            assert com_sla.prazo_cobertura_solicitacoes == 1
    finally:
        await engine.dispose()
