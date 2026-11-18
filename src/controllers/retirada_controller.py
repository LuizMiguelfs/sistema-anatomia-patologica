"""Controller de Solicitações de Exames (MVP): listas "Não retirados" e "Retirados".

A solicitação entra no SAP já recebida (aberta a partir do AGHU, com código interno) e fica
em "Não retirados" até a Recepção marcar que o material foi retirado. Marcar como retirado
encerra a etapa RECEPCAO e leva a solicitação à próxima fase do seu tipo de exame; desfazer
devolve a solicitação para "Não retirados" enquanto a fase seguinte ainda não começou.
Toda mutação grava movimentação e auditoria na mesma transação (RN-04).
"""
import logging
import re
from typing import Any, Dict, Optional

from fastapi import HTTPException

from ..providers.interfaces.solicitacao_provider_interface import SolicitacaoProviderInterface
from .solicitacao_controller import (
    PERFIL_RECEPCAO, STATUS_ARQUIVADO, TIPOS_EXAME, _agora, _solicitacao_ou_404, _exigir_perfil,
    _exigir_sem_pendencias, _gravar, _login, _status_derivado,
)

logger = logging.getLogger("solicitacoes")

SITUACOES = {"NAO_RETIRADO", "RETIRADO"}
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _data_ou_none(valor: Optional[str], campo: str) -> Optional[str]:
    """Data no formato AAAA-MM-DD, ou None; 422 se inválida."""
    texto = (valor or "").strip()
    if not texto:
        return None
    if not _DATA.match(texto):
        raise HTTPException(status_code=422, detail=f"Data inválida em '{campo}'. Use o formato AAAA-MM-DD.")
    return texto


def normalizar_filtros_busca(filtros: Dict[str, Any]) -> Dict[str, Any]:
    """Tipo de exame (em maiúsculas, validado) e busca única pelos três códigos do dia a dia."""
    tipo = (filtros.get("tipo_exame") or "").strip().upper() or None
    if tipo and tipo not in TIPOS_EXAME:
        raise HTTPException(status_code=422, detail="Tipo de exame inválido.")
    busca = (filtros.get("busca") or "").strip() or None
    return {"tipo_exame": tipo, "busca": busca}


async def listar_solicitacoes(
    situacao: str, filtros: Dict[str, Any], pagina: int, limite: int, provider: SolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Lista "Não retirados" (urgentes no topo, mais antigo primeiro) ou "Retirados" (mais recente primeiro)."""
    situacao = (situacao or "").strip().upper()
    if situacao not in SITUACOES:
        raise HTTPException(status_code=422, detail="Situação inválida: use NAO_RETIRADO ou RETIRADO.")
    pagina = max(pagina, 1)
    limite = min(max(limite, 1), 100)
    limpos = {
        **normalizar_filtros_busca(filtros),
        "situacao": situacao,
        "de": _data_ou_none(filtros.get("de"), "de"),
        "ate": _data_ou_none(filtros.get("ate"), "ate"),
    }
    itens = await provider.listar_solicitacoes(limpos, limite, (pagina - 1) * limite)
    total = await provider.contar_solicitacoes(limpos)
    return {"items": [_item(i) for i in itens], "total": total, "pagina": pagina, "limite": limite}


def _item(linha: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza tipos vindos do SQLite (urgente 0/1)."""
    return {**linha, "urgente": bool(linha.get("urgente"))}


async def marcar_retirado(
    solicitacao_id: int, usuario: Dict[str, Any], ip: Optional[str], provider: SolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Recepção marca o material como retirado: encerra a etapa RECEPCAO e avança para a próxima fase."""
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "marcar o material como retirado")
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    if solicitacao["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail="Solicitação já arquivada.")
    if solicitacao.get("retirado_em") or solicitacao["etapa_atual"] != "RECEPCAO":
        raise HTTPException(status_code=409, detail="Esta solicitação já foi marcada como retirada.")
    await _exigir_sem_pendencias(provider, solicitacao_id)
    proximas = await provider.destinos(solicitacao["tipo_exame"], "RECEPCAO", "AVANCO")
    if not proximas:
        raise HTTPException(status_code=409, detail=f"Fluxo do exame {solicitacao['tipo_exame']} não está configurado após a Recepção.")
    destino = proximas[0]
    status = _status_derivado(destino)
    agora = _agora()
    login = _login(usuario)
    try:
        await provider.marcar_retirada(solicitacao_id, destino, status, login, agora)
        await provider.inserir_movimentacao({
            "solicitacao_id": solicitacao_id, "tipo": "RETIRADA", "etapa_origem": "RECEPCAO",
            "etapa_destino": destino, "motivo": None, "usuario": login, "agora": agora,
        })
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="MARCAR_RETIRADO", solicitacao_id=solicitacao_id,
            anteriores={"etapa_atual": "RECEPCAO", "retirado_em": None},
            novos={"etapa_atual": destino, "retirado_em": agora, "retirado_por": login},
        )
        await provider.commit()
    except Exception as erro:
        await provider.rollback()
        logger.error("Falha em %s: %s", "MARCAR_RETIRADO", erro.__class__.__name__)
        raise
    return {"id": solicitacao_id, "etapa_atual": destino, "retirado_em": agora, "retirado_por": login}


async def desfazer_retirada(
    solicitacao_id: int, usuario: Dict[str, Any], ip: Optional[str], provider: SolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Recepção desfaz a retirada enquanto a fase seguinte não registrou nada; a ação fica auditada."""
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "desfazer a retirada")
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    if not solicitacao.get("retirado_em"):
        raise HTTPException(status_code=409, detail="Esta solicitação não está marcada como retirada.")
    proximas = await provider.destinos(solicitacao["tipo_exame"], "RECEPCAO", "AVANCO")
    etapa = solicitacao["etapa_atual"]
    if solicitacao["status"] == STATUS_ARQUIVADO or etapa not in proximas or await provider.buscar_fase(solicitacao_id, etapa):
        raise HTTPException(
            status_code=409,
            detail="A fase seguinte já começou a registrar esta solicitação; não é possível desfazer a retirada.",
        )
    status = _status_derivado("RECEPCAO")
    agora = _agora()
    login = _login(usuario)
    try:
        await provider.desfazer_retirada(solicitacao_id, status, agora)
        await provider.inserir_movimentacao({
            "solicitacao_id": solicitacao_id, "tipo": "DESFAZER_RETIRADA", "etapa_origem": etapa,
            "etapa_destino": "RECEPCAO", "motivo": None, "usuario": login, "agora": agora,
        })
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="DESFAZER_RETIRADA", solicitacao_id=solicitacao_id,
            anteriores={"etapa_atual": etapa, "retirado_em": solicitacao["retirado_em"], "retirado_por": solicitacao.get("retirado_por")},
            novos={"etapa_atual": "RECEPCAO", "retirado_em": None},
        )
        await provider.commit()
    except Exception as erro:
        await provider.rollback()
        logger.error("Falha em %s: %s", "DESFAZER_RETIRADA", erro.__class__.__name__)
        raise
    return {"id": solicitacao_id, "etapa_atual": "RECEPCAO", "retirado_em": None, "retirado_por": None}
