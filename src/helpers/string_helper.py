"""
Helper de Strings: normalização e validação de documentos (CPF / CNS) e nomes
=============================================================================
Funções puras, sem acesso a banco, reutilizáveis por qualquer controller.
"""

import re
import unicodedata
from typing import Optional


def somente_digitos(valor: Optional[str]) -> str:
    """Remove tudo o que não for dígito (ex.: '111.444.777-35' -> '11144477735')."""
    return re.sub(r"\D", "", valor or "")


def remover_acentos(texto: str) -> str:
    """Remove acentos/diacríticos de um texto (ex.: 'João' -> 'Joao')."""
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def normalizar_para_busca(texto: Optional[str]) -> str:
    """Normaliza texto para comparação: sem acentos, minúsculo e sem espaços extras."""
    return " ".join(remover_acentos(texto or "").casefold().split())


def normalizar_nome(nome: Optional[str]) -> Optional[str]:
    """Padroniza nomes de pessoas no formato do AGHU: maiúsculas e espaços simples."""
    if nome is None:
        return None
    limpo = " ".join(nome.split()).upper()
    return limpo or None


def validar_cpf(cpf: str) -> bool:
    """Valida um CPF (11 dígitos) pelos dígitos verificadores. Aceita entrada formatada."""
    digitos = somente_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(int(digitos[i]) * (posicao + 1 - i) for i in range(posicao))
        verificador = (soma * 10) % 11 % 10
        if verificador != int(digitos[posicao]):
            return False
    return True


def validar_cns(cns: str) -> bool:
    """Valida um Cartão Nacional de Saúde (15 dígitos) pela regra oficial do DATASUS."""
    digitos = somente_digitos(cns)
    # Definitivos começam com 1 ou 2; provisórios com 7, 8 ou 9.
    if len(digitos) != 15 or digitos[0] not in "12789":
        return False
    # Em ambos os casos a soma ponderada (pesos 15..1) deve ser múltipla de 11.
    soma = sum(int(digitos[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0


def formatar_cpf(cpf: Optional[str]) -> Optional[str]:
    """Formata CPF como 000.000.000-00; retorna None se vazio ou inválido no tamanho."""
    digitos = somente_digitos(cpf)
    if len(digitos) != 11:
        return None
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
