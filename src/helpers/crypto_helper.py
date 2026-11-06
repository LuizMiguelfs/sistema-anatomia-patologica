"""
Criptografia de dados sensíveis em repouso (AES-256)
=====================================================
Regra do SPEC.md: dados sensíveis gravados pelo SAP usam AES-256. Aqui: AES-256-GCM
(cifra autenticada), com nonce aleatório de 12 bytes por valor.

Só é cifrado o que identifica um único paciente (CAMPOS_PACIENTE): nome, documentos,
prontuário, filiação e data de nascimento. O restante fica legível para consulta.
Para buscar por um valor cifrado (ex.: prontuário) usa-se `indice_busca` (HMAC-SHA256).

Chave: variável de ambiente SAP_DATA_KEY, 32 bytes em base64 (ver .env.example).
Formato gravado: "aes256gcm:v1:" + base64(nonce + texto cifrado + tag).
Valores sem esse prefixo são lidos como texto puro (registros anteriores a esta versão).
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
from functools import lru_cache
from typing import Any, Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIXO = "aes256gcm:v1:"
_TAMANHO_NONCE = 12

#: Campos que, sozinhos ou juntos, identificam um único paciente (cifrados com AES-256).
CAMPOS_PACIENTE = frozenset({
    "nome", "paciente_nome", "nome_paciente", "nome_mae", "nome_pai",
    "cpf", "cns", "dt_nascimento", "data_nascimento", "prontuario", "prontuario_aghu",
})


class ChaveCriptografiaInvalidaError(RuntimeError):
    """SAP_DATA_KEY ausente ou fora do formato (32 bytes em base64)."""


class DadoCifradoInvalidoError(ValueError):
    """Valor cifrado corrompido ou gravado com outra chave."""


def validar_chave(valor: Optional[str]) -> bytes:
    """Decodifica e valida a chave AES-256 (32 bytes em base64)."""
    try:
        chave = base64.b64decode((valor or "").strip(), validate=True)
    except (binascii.Error, ValueError):
        chave = b""
    if len(chave) != 32:
        raise ChaveCriptografiaInvalidaError("SAP_DATA_KEY deve ter 32 bytes codificados em base64 (AES-256).")
    return chave


@lru_cache(maxsize=1)
def _cifra() -> AESGCM:
    """Instância AES-256-GCM com a chave do ambiente (carregada uma vez)."""
    return AESGCM(validar_chave(os.getenv("SAP_DATA_KEY")))


def cifrar(texto: Optional[str]) -> Optional[str]:
    """Cifra um texto com AES-256-GCM. `None` continua `None`."""
    if texto is None:
        return None
    nonce = os.urandom(_TAMANHO_NONCE)
    cifrado = _cifra().encrypt(nonce, texto.encode("utf-8"), None)
    return PREFIXO + base64.b64encode(nonce + cifrado).decode("ascii")


def decifrar(valor: Optional[str]) -> Optional[str]:
    """Decifra um valor gravado por `cifrar`. Texto sem prefixo é devolvido como está."""
    if valor is None or not valor.startswith(PREFIXO):
        return valor
    try:
        bruto = base64.b64decode(valor[len(PREFIXO):], validate=True)
        texto = _cifra().decrypt(bruto[:_TAMANHO_NONCE], bruto[_TAMANHO_NONCE:], None)
    except (binascii.Error, ValueError, InvalidTag):
        # Sem detalhes do conteúdo na mensagem (RNF007).
        raise DadoCifradoInvalidoError("Dado cifrado inválido ou gravado com outra chave.") from None
    return texto.decode("utf-8")


def cifrar_campos_paciente(dados: Any) -> Any:
    """Cifra, em qualquer nível de dicionários e listas, os valores dos CAMPOS_PACIENTE."""
    if isinstance(dados, dict):
        return {
            chave: (cifrar(json.dumps(valor, ensure_ascii=False, default=str))
                    if chave in CAMPOS_PACIENTE and valor is not None else cifrar_campos_paciente(valor))
            for chave, valor in dados.items()
        }
    if isinstance(dados, list):
        return [cifrar_campos_paciente(item) for item in dados]
    return dados


def decifrar_campos(dados: Any) -> Any:
    """Inverso de `cifrar_campos_paciente`: decifra todo texto com o prefixo AES-256."""
    if isinstance(dados, dict):
        return {chave: decifrar_campos(valor) for chave, valor in dados.items()}
    if isinstance(dados, list):
        return [decifrar_campos(item) for item in dados]
    if isinstance(dados, str) and dados.startswith(PREFIXO):
        return json.loads(decifrar(dados))
    return dados


@lru_cache(maxsize=1)
def _chave_indice() -> bytes:
    """Chave do índice de busca, derivada da SAP_DATA_KEY (separada da chave de cifra)."""
    return hmac.new(validar_chave(os.getenv("SAP_DATA_KEY")), b"sap-indice-busca-v1", hashlib.sha256).digest()


def normalizar_prontuario(valor: Optional[str]) -> str:
    """Só os dígitos do prontuário: "1903344/8" e "19033448" são o mesmo prontuário."""
    return re.sub(r"\D", "", valor or "")


def indice_busca(valor: Optional[str]) -> Optional[str]:
    """
    Índice determinístico (HMAC-SHA256) para busca exata de um valor cifrado.
    Não permite recuperar o valor; `None` ou vazio devolve `None`.
    """
    if not valor:
        return None
    return hmac.new(_chave_indice(), valor.encode("utf-8"), hashlib.sha256).hexdigest()
