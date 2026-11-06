"""
Controller de Auditoria (consulta da trilha `audit_logs`)
==========================================================
Regras da consulta: validação do período, conversão do dia local para UTC, filtro por prefixo,
restrição do histórico a eventos de negócio e formatação da saída (JSON devolvido como objeto).
Somente leitura: a gravação de eventos é feita por `helpers/audit_helper.registrar_auditoria`.
O acesso ao banco é feito apenas pelo provedor (`AuditoriaProviderInterface`).
"""

import json
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from ..helpers.crypto_helper import decifrar_campos
from ..providers.interfaces.auditoria_provider_interface import AuditoriaProviderInterface

#: Categoria exibida no histórico de um caso/recurso, aberto a qualquer usuário autenticado.
CATEGORIA_HISTORICO = "NEGOCIO_CLINICO"


def _json_ou_texto(valor: Optional[str]) -> Any:
    """Converte o JSON salvo de volta em objeto (com os campos do paciente decifrados)."""
    if valor is None:
        return None
    try:
        return decifrar_campos(json.loads(valor))
    except (TypeError, ValueError):
        return valor


def serializar_log(registro: Dict[str, Any]) -> Dict[str, Any]:
    """Formato de saída de um registro: dados anteriores/novos como objetos."""
    return {
        **registro,
        "dados_anteriores": _json_ou_texto(registro.get("dados_anteriores")),
        "dados_novos": _json_ou_texto(registro.get("dados_novos")),
    }


def _pagina(total: int, limite: int, offset: int, registros: list) -> Dict[str, Any]:
    """Monta a resposta paginada padrão."""
    return {"total": total, "limite": limite, "offset": offset, "itens": [serializar_log(r) for r in registros]}


async def listar_logs(
    provider: AuditoriaProviderInterface,
    usuario: Optional[str] = None,
    categoria: Optional[str] = None,
    acao: Optional[str] = None,
    recurso: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limite: int = 50,
    offset: int = 0,
    utc_offset_minutos: int = 0,
) -> Dict[str, Any]:
    """
    Consulta administrativa da trilha de auditoria, com filtros combináveis.
    - `usuario`: login exato (sem diferenciar maiúsculas/minúsculas).
    - `acao`: nome exato da ação (ex.: CRIAR_PACIENTE).
    - `recurso`: exato (ex.: paciente:123) ou por prefixo terminando em `*` (ex.: paciente:*).
    - `data_inicio` / `data_fim`: dias inclusivos no fuso de quem consulta.
    - `utc_offset_minutos`: fuso de quem consulta em relação ao UTC (Recife = -180).
      Os registros são gravados em UTC; o dia local é convertido para o intervalo UTC.
    """
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial não pode ser posterior à data final.",
        )

    fuso = timedelta(minutes=utc_offset_minutos)
    recurso = (recurso or "").strip() or None
    filtros = {
        "usuario": (usuario or "").strip() or None,
        "categoria": categoria.upper() if categoria else None,
        "acao": (acao or "").strip().upper() or None,
        "recurso": None if recurso is None or recurso.endswith("*") else recurso,
        "recurso_prefixo": recurso[:-1] if recurso and recurso.endswith("*") else None,
        "inicio": datetime.combine(data_inicio, time.min) - fuso if data_inicio else None,
        "fim": datetime.combine(data_fim + timedelta(days=1), time.min) - fuso if data_fim else None,
    }

    total = await provider.contar_logs(**filtros)
    registros = await provider.listar_logs(**filtros, limite=limite, offset=offset)
    return _pagina(total, limite, offset, registros)


async def historico_recurso(
    provider: AuditoriaProviderInterface,
    recurso: str,
    limite: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Linha do tempo de um recurso (ex.: caso:123) para qualquer usuário autenticado (RF021).
    Mostra apenas eventos NEGOCIO_CLINICO e não expõe o IP de origem.
    """
    recurso = recurso.strip()
    total = await provider.contar_historico(recurso, CATEGORIA_HISTORICO)
    registros = await provider.listar_historico(recurso, CATEGORIA_HISTORICO, limite=limite, offset=offset)
    return _pagina(total, limite, offset, registros)
