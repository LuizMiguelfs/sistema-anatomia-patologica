# tests/test_audit_helper.py
"""Helper `registrar_auditoria`: categorias obrigatórias e gravação na mesma transação (RN-04)."""

import sqlite3

import pytest

from src.helpers.audit_helper import registrar_auditoria
from tests.auditoria_helpers import _com_sessao, _gravar, ambiente  # noqa: F401


def test_helper_rejeita_categoria_invalida(ambiente):
    client, _ = ambiente
    with pytest.raises(ValueError):
        _gravar(client, categoria="QUALQUER")


def test_helper_commit_false_grava_junto_com_a_transacao(ambiente):
    """Com commit=False o log só é gravado no commit do chamador; rollback descarta os dois."""
    client, db_path = ambiente

    async def _rollback(session):
        await registrar_auditoria(session, "joao.silva", "NEGOCIO_CLINICO", "ACAO_DESFEITA",
                                  "caso:1", commit=False)
        await session.rollback()

    async def _commit(session):
        await registrar_auditoria(session, "joao.silva", "NEGOCIO_CLINICO", "ACAO_CONFIRMADA",
                                  "caso:1", commit=False)
        await session.commit()

    _com_sessao(client, _rollback)
    _com_sessao(client, _commit)
    with sqlite3.connect(db_path) as conn:
        acoes = [r[0] for r in conn.execute("SELECT acao FROM audit_logs")]
    assert acoes == ["ACAO_CONFIRMADA"]
