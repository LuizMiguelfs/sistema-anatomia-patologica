# tests/test_crypto_helper.py
"""AES-256 para dados que identificam o paciente (SPEC.md): helper, índice de busca e auditoria."""

import base64
import json
import os
import sqlite3

import pytest

from src.helpers import crypto_helper
from src.helpers.crypto_helper import (
    PREFIXO, ChaveCriptografiaInvalidaError, DadoCifradoInvalidoError, cifrar, cifrar_campos_paciente,
    decifrar, decifrar_campos, indice_busca, normalizar_prontuario, validar_chave,
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


def test_cifra_so_os_campos_do_paciente_em_qualquer_nivel():
    dados = {"nome": "MARIA", "cpf": "52998224725", "sexo": "F", "amostras": [{"prontuario": "123"}], "obs": None}
    cifrado = cifrar_campos_paciente(dados)
    assert cifrado["nome"].startswith(PREFIXO) and cifrado["cpf"].startswith(PREFIXO)
    assert cifrado["amostras"][0]["prontuario"].startswith(PREFIXO)
    assert cifrado["sexo"] == "F" and cifrado["obs"] is None  # não identifica o paciente
    assert decifrar_campos(cifrado) == dados


def test_indice_de_busca_deterministico_e_sem_o_valor():
    assert indice_busca("19033448") == indice_busca("19033448") != indice_busca("19033449")
    assert "19033448" not in indice_busca("19033448")
    assert indice_busca("") is None and indice_busca(None) is None
    assert normalizar_prontuario("1903344/8") == normalizar_prontuario(" 19033448 ") == "19033448"


def test_auditoria_clinica_cifra_so_dados_do_paciente_e_api_devolve_legivel(ambiente):
    client, db_path = ambiente
    _gravar(client, dados_anteriores={"cpf": "52998224725", "sexo": "F"}, dados_novos={"nome": "MARIA"})
    _gravar(client, categoria="SEGURANCA", acao="ALTERAR_PERFIL_USUARIO", recurso="usuario:joao.silva",
            dados_anteriores={"perfil": "RECEPCAO"}, dados_novos={"nome": "João da Silva"})
    with sqlite3.connect(db_path) as conn:
        clinico, seguranca = conn.execute(
            "SELECT dados_anteriores, dados_novos FROM audit_logs ORDER BY id").fetchall()
    antes = json.loads(clinico[0])
    assert antes["cpf"].startswith(PREFIXO) and antes["sexo"] == "F"
    assert "52998224725" not in clinico[0] and "MARIA" not in clinico[1]
    # Fora de NEGOCIO_CLINICO nada é cifrado (ex.: nome do servidor na gestão de usuários).
    assert json.loads(seguranca[1]) == {"nome": "João da Silva"}

    itens = client.get("/api/admin/auditoria", headers=_admin(client)).json()["itens"]
    clinico_api = next(i for i in itens if i["categoria"] == "NEGOCIO_CLINICO")
    assert clinico_api["dados_anteriores"] == {"cpf": "52998224725", "sexo": "F"}
    assert clinico_api["dados_novos"] == {"nome": "MARIA"}
