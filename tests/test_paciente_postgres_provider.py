# tests/test_paciente_postgres_provider.py
"""
Testes de integração do PacientePostgresProvider contra um PostgreSQL REAL de teste.

São ignorados (skip) se a variável PACIENTE_TEST_POSTGRES_DSN não estiver definida.
NUNCA aponte para o AGHU: o teste cria/derruba o schema `agh` no banco informado.
    Ex.: PACIENTE_TEST_POSTGRES_DSN=postgresql+asyncpg://postgres@localhost:5432/teste_sap
"""

import os
from datetime import date

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.providers.implementations.paciente_postgres_provider import PacientePostgresProvider

DSN = os.getenv("PACIENTE_TEST_POSTGRES_DSN")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not DSN, reason="PACIENTE_TEST_POSTGRES_DSN não definida"),
]

SCHEMA_SQL = [
    "DROP SCHEMA IF EXISTS agh CASCADE",
    "CREATE SCHEMA agh",
    """CREATE TABLE agh.aip_pacientes (
        codigo SERIAL PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        dt_nascimento TIMESTAMP,
        sexo VARCHAR(1),
        cor VARCHAR(20),
        nome_mae VARCHAR(100),
        nome_pai VARCHAR(100)
    )""",
    """INSERT INTO agh.aip_pacientes (codigo, nome, dt_nascimento, sexo, cor, nome_mae, nome_pai) VALUES
        (500, 'ZULEIDE PEREIRA', '1970-01-02 00:00:00', 'F', 'B', 'MAE Z', NULL),
        (501, 'ANTONIO CARLOS', '1980-03-04 00:00:00', 'M', 'P', 'MAE A', 'PAI A'),
        (502, 'MARIA ANTONIA', NULL, 'F', NULL, NULL, NULL)""",
    "SELECT setval('agh.aip_pacientes_codigo_seq', 502)",
]


@pytest_asyncio.fixture
async def sessao():
    """Recria o schema `agh` de teste e fornece uma sessão assíncrona."""
    engine = create_async_engine(DSN)
    async with engine.begin() as conn:
        for sql in SCHEMA_SQL:
            await conn.execute(text(sql))
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS agh CASCADE"))
    await engine.dispose()


async def test_listar_ordenado_e_normalizado(sessao):
    provider = PacientePostgresProvider(sessao)
    pacientes = await provider.listar_pacientes()
    assert [p["nome"] for p in pacientes] == ["ANTONIO CARLOS", "MARIA ANTONIA", "ZULEIDE PEREIRA"]
    assert pacientes[0]["dt_nascimento"] == date(1980, 3, 4)  # TIMESTAMP -> date
    assert pacientes[1]["dt_nascimento"] is None
    assert pacientes[0]["cpf"] is None


async def test_busca_por_nome_codigo_e_paginacao(sessao):
    provider = PacientePostgresProvider(sessao)
    assert [p["codigo"] for p in await provider.listar_pacientes(termo="antoni")] == [501, 502]
    assert [p["codigo"] for p in await provider.listar_pacientes(termo="500")] == [500]
    assert [p["codigo"] for p in await provider.listar_pacientes(limite=1, offset=1)] == [502]
    assert await provider.listar_pacientes(termo="inexistente") == []


async def test_obter(sessao):
    provider = PacientePostgresProvider(sessao)
    assert (await provider.obter_paciente_por_codigo(501))["nome_pai"] == "PAI A"
    assert await provider.obter_paciente_por_codigo(999) is None


async def test_escrita_bloqueada_por_padrao_nao_altera_o_banco(sessao):
    provider = PacientePostgresProvider(sessao)  # escrita_habilitada=False
    assert provider.capacidades() == {"escrita": False, "exclusao": False}
    dados = {"nome": "NOVO", "dt_nascimento": date(2000, 1, 1), "sexo": "M"}
    with pytest.raises(PermissionError):
        await provider.criar_paciente(dados)
    with pytest.raises(PermissionError):
        await provider.atualizar_paciente(500, dados)
    with pytest.raises(PermissionError):
        await provider.excluir_paciente(500)
    total = (await sessao.execute(text("SELECT COUNT(*) FROM agh.aip_pacientes"))).scalar()
    assert total == 3


async def test_escrita_habilitada_insere_e_atualiza(sessao):
    provider = PacientePostgresProvider(sessao, escrita_habilitada=True)
    criado = await provider.criar_paciente(
        {"nome": "NOVO PACIENTE", "dt_nascimento": date(2001, 2, 3), "sexo": "F", "cor": None,
         "nome_mae": "MAE N", "nome_pai": None, "cpf": "529.982.247-25"}
    )
    assert criado["codigo"] == 503 and criado["dt_nascimento"] == date(2001, 2, 3)

    atualizado = await provider.atualizar_paciente(
        503, {"nome": "NOVO EDITADO", "dt_nascimento": date(2001, 2, 4), "sexo": "F"}
    )
    assert atualizado["nome"] == "NOVO EDITADO" and atualizado["nome_mae"] is None
    assert await provider.atualizar_paciente(999, {"nome": "X", "dt_nascimento": date(2000, 1, 1)}) is None
    # Exclusão continua proibida mesmo com escrita habilitada (sem soft delete no AGHU)
    with pytest.raises(PermissionError):
        await provider.excluir_paciente(503)


async def test_falha_de_banco_vira_503_sem_vazar_detalhes():
    engine = create_async_engine("postgresql+asyncpg://ninguem:x@127.0.0.1:1/inexistente")
    async with AsyncSession(engine) as session:
        with pytest.raises(HTTPException) as exc:
            await PacientePostgresProvider(session).listar_pacientes()
    await engine.dispose()
    assert exc.value.status_code == 503
    assert "ninguem" not in exc.value.detail
