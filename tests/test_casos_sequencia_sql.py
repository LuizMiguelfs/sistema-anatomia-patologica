"""Numeração do identificador interno no SQLite real (tabela criada pela migração do módulo de casos)."""
import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.providers.implementations.caso_postgres_provider import CasoPostgresProvider


def test_proximo_numero_por_sigla_e_ano(tmp_path, monkeypatch):
    dsn = f"sqlite+aiosqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("SQLITE_DSN", dsn)
    command.upgrade(Config("alembic.ini"), "head")  # o env.py do Alembic roda o próprio loop

    async def _verificar():
        engine = create_async_engine(dsn)
        try:
            async with async_sessionmaker(engine)() as session:
                provider = CasoPostgresProvider(session)
                seq = [await provider.proximo_numero(s, a)
                       for s, a in [("HP", 2026), ("HP", 2026), ("CG", 2026), ("HP", 2027), ("HP", 2026)]]
                await session.rollback()  # reserva desfeita junto com a transação do caso
                assert seq == [1, 2, 1, 1, 3]
                assert await provider.proximo_numero("HP", 2026) == 1
        finally:
            await engine.dispose()

    asyncio.run(_verificar())
