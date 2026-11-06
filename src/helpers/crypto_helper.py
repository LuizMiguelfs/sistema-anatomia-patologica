"""
Criptografia de dados sensíveis em repouso (AES-256)
=====================================================
Regra do SPEC.md: dados sensíveis gravados pelo SAP usam AES-256. Aqui: AES-256-GCM
(cifra autenticada), com nonce aleatório de 12 bytes por valor.

Chave: variável de ambiente SAP_DATA_KEY, 32 bytes em base64 (ver .env.example).
Formato gravado: "aes256gcm:v1:" + base64(nonce + texto cifrado + tag).
Valores sem esse prefixo são lidos como texto puro (registros anteriores a esta versão).
"""

import base64
import binascii
import os
from functools import lru_cache
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIXO = "aes256gcm:v1:"
_TAMANHO_NONCE = 12


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
