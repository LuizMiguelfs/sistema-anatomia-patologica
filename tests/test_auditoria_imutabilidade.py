# tests/test_auditoria_imutabilidade.py
"""Trilha de auditoria: a tabela sempre existe e nenhum registro pode ser alterado ou apagado."""

import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from src.main import app
from src.models.audit_log import AuditLog, AuditLogImutavelError
from tests.auditoria_helpers import _com_sessao, _gravar, ambiente  # noqa: F401


def test_tabela_criada_na_inicializacao(ambiente):
    _, db_path = ambiente
    with sqlite3.connect(db_path) as conn:
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "audit_logs" in tabelas


def test_orm_bloqueia_alteracao_e_exclusao(ambiente):
    client, _ = ambiente
    log_id = _gravar(client)

    async def _alterar(session):
        log = await session.get(AuditLog, log_id)
        log.acao = "ADULTERADA"
        await session.commit()

    async def _apagar(session):
        log = await session.get(AuditLog, log_id)
        await session.delete(log)
        await session.commit()

    with pytest.raises(AuditLogImutavelError):
        _com_sessao(client, _alterar)
    with pytest.raises(AuditLogImutavelError):
        _com_sessao(client, _apagar)


def test_banco_bloqueia_update_e_delete_em_sql_direto(ambiente):
    client, db_path = ambiente
    _gravar(client)
    with sqlite3.connect(db_path) as conn:
        with pytest.raises(sqlite3.DatabaseError, match="imutavel"):
            conn.execute("UPDATE audit_logs SET acao = 'X'")
        with pytest.raises(sqlite3.DatabaseError, match="imutavel"):
            conn.execute("DELETE FROM audit_logs")

    async def _em_massa(session):
        await session.execute(delete(AuditLog))
        await session.commit()

    with pytest.raises(IntegrityError):
        _com_sessao(client, _em_massa)


def test_triggers_protegem_banco_criado_antes(tmp_path, monkeypatch):
    """Banco com audit_logs já existente (versão anterior, sem triggers) passa a ser protegido."""
    db_path = tmp_path / "antigo.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, created_at DATETIME NOT NULL, "
            "usuario VARCHAR NOT NULL, categoria VARCHAR NOT NULL, acao VARCHAR NOT NULL, "
            "recurso VARCHAR NOT NULL, dados_anteriores TEXT, dados_novos TEXT, ip_origem VARCHAR)"
        )
        conn.execute("INSERT INTO audit_logs VALUES (1, '2026-01-01', 'a', 'SEGURANCA', 'LOGIN', 'sessao', NULL, NULL, NULL)")
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db_path}")
    with TestClient(app):
        pass
    with sqlite3.connect(db_path) as conn:
        with pytest.raises(sqlite3.DatabaseError, match="imutavel"):
            conn.execute("DELETE FROM audit_logs")
