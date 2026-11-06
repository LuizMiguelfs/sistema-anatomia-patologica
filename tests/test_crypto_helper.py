# tests/test_crypto_helper.py
"""AES-256 para dados sensíveis (SPEC.md): helper de criptografia e gravação cifrada da auditoria."""

import base64
import json
import os
import sqlite3

import pytest

from src.helpers import crypto_helper
from src.helpers.crypto_helper import (
    PREFIXO, ChaveCriptografiaInvalidaError, DadoCifradoInvalidoError, cifrar, decifrar, validar_chave,
)
from tests.auditoria_helpers import _admin, _gravar, ambiente  # noqa: F401


def test_cifra_e_decifra_com_nonce_aleatorio():
    texto = '{"nome": "MARIA DA SILVA", "cpf": "52998224725"}'
    a, b = cifrar(texto), cifrar(texto)
    assert a.startswith(PREFIXO) and a != b  # mesmo texto, cifras diferentes
    assert "MARIA" not in a
    assert decifrar(a) == decifrar(b) == texto


def test_none_e_texto_legado_passam_direto():
    assert cifrar(None) is None and decifrar(None) is None
    assert decifrar('{"antigo": true}') == '{"antigo": true}'


def test_dado_adulterado_e_rejeitado():
    cifrado = cifrar("segredo")
    bruto = bytearray(base64.b64decode(cifrado[len(PREFIXO):]))
    bruto[-1] ^= 1
    with pytest.raises(DadoCifradoInvalidoError):
        decifrar(PREFIXO + base64.b64encode(bytes(bruto)).decode())


@pytest.mark.parametrize("chave", ["", "curta", base64.b64encode(os.urandom(16)).decode(), "não é base64!"])
def test_chave_invalida_e_recusada(chave):
    with pytest.raises(ChaveCriptografiaInvalidaError):
        validar_chave(chave)


def test_chave_diferente_nao_le_o_dado(monkeypatch):
    cifrado = cifrar("segredo")
    monkeypatch.setenv("SAP_DATA_KEY", base64.b64encode(os.urandom(32)).decode())
    crypto_helper._cifra.cache_clear()
    try:
        with pytest.raises(DadoCifradoInvalidoError):
            decifrar(cifrado)
    finally:
        monkeypatch.undo()
        crypto_helper._cifra.cache_clear()


def test_auditoria_grava_antes_e_depois_cifrados_e_api_devolve_legivel(ambiente):
    client, db_path = ambiente
    _gravar(client, dados_anteriores={"cpf": "52998224725"}, dados_novos={"nome": "MARIA"})
    with sqlite3.connect(db_path) as conn:
        antes, depois = conn.execute("SELECT dados_anteriores, dados_novos FROM audit_logs").fetchone()
    assert antes.startswith(PREFIXO) and depois.startswith(PREFIXO)
    assert "52998224725" not in antes and "MARIA" not in depois
    assert json.loads(decifrar(antes)) == {"cpf": "52998224725"}

    item = client.get("/api/admin/auditoria", headers=_admin(client)).json()["itens"][0]
    assert item["dados_anteriores"] == {"cpf": "52998224725"}
    assert item["dados_novos"] == {"nome": "MARIA"}
