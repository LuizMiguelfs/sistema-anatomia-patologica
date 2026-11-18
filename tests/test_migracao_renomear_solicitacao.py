"""Migração 20261118_renomear_solicitacao (T4.1) num banco que já subiu o código novo.

Em desenvolvimento o sistema cria as tabelas que faltam ao subir (create_all). Quem sobe o código
novo antes de migrar fica com as tabelas novas, vazias, ao lado das antigas, que têm os dados.
"""
import sqlite3

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from src.models import solicitacao  # noqa: F401  (registra as tabelas novas no metadata)
from src.resources.database import Base


def _banco_com_tabelas_antigas(tmp_path, monkeypatch):
    """Banco na revisão anterior (tabelas de 'caso') com uma solicitação e uma movimentação."""
    db = tmp_path / "app.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db}")
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "20261111_mvp_fases")
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO casos (identificador_interno, solicitacao_aghu, paciente_codigo_aghu, paciente_nome, tipo_exame,"
            " etapa_atual, status, criado_por, criado_em, atualizado_em) VALUES"
            " ('HP-0001/26', '500001', '1', 'cifrado', 'HP', 'RECEPCAO', 'EM_ANDAMENTO', 'x', '2026', '2026')"
        )
        conn.execute(
            "INSERT INTO caso_movimentacoes (caso_id, tipo, usuario, criado_em) VALUES (1, 'ABERTURA', 'x', '2026')"
        )
    return db, cfg


def _subir_codigo_novo(db):
    """O que o sistema faz ao subir em desenvolvimento: cria as tabelas que faltam."""
    engine = create_engine(f"sqlite:///{db}")
    Base.metadata.create_all(engine)
    engine.dispose()


def test_tabelas_novas_vazias_dao_lugar_as_antigas(tmp_path, monkeypatch):
    db, cfg = _banco_com_tabelas_antigas(tmp_path, monkeypatch)
    _subir_codigo_novo(db)
    command.upgrade(cfg, "head")
    with sqlite3.connect(db) as conn:
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "casos" not in tabelas and "caso_movimentacoes" not in tabelas
        assert conn.execute("SELECT identificador_interno FROM solicitacoes_exame").fetchall() == [("HP-0001/26",)]
        assert conn.execute("SELECT solicitacao_id FROM solicitacao_movimentacoes").fetchall() == [(1,)]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_tabela_nova_com_dados_para_sem_apagar_nada(tmp_path, monkeypatch):
    db, cfg = _banco_com_tabelas_antigas(tmp_path, monkeypatch)
    _subir_codigo_novo(db)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO solicitacao_sequencias (sigla, ano, ultimo) VALUES ('HP', 2026, 3)")
    with pytest.raises(RuntimeError, match="solicitacao_sequencias"):
        command.upgrade(cfg, "head")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone() == ("20261111_mvp_fases",)
        assert conn.execute("SELECT COUNT(*) FROM casos").fetchone() == (1,)
        assert conn.execute("SELECT COUNT(*) FROM solicitacao_sequencias").fetchone() == (1,)
