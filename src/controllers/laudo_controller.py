"""Fluxo de revisão, evento fictício de liberação e arquivamento da solicitação (T08).

O SAP não libera nem escreve laudos no AGHU. O evento de liberação desta entrega é
exclusivamente de demonstração, indisponível em produção e auditado como simulado.
"""
import os
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from ..auth.auth import ENV, MockAuthProvider, auth_handler
from ..providers.interfaces.solicitacao_provider_interface import SolicitacaoProviderInterface
from .solicitacao_controller import (
    PERFIL_PRECEPTORIA, STATUS_ARQUIVADO, _agora, _exigir_perfil,
    _exigir_sem_pendencias, _gravar, _login, _solicitacao_ou_404,
)

logger = logging.getLogger("laudos")
STATUS_AGUARDANDO_LIBERACAO = "AGUARDANDO_LIBERACAO"
STATUS_LAUDO_LIBERADO = "LAUDO_LIBERADO"
def _demo_habilitada() -> bool:
    """Nunca simula laudo hospitalar com fonte AGHU real, mesmo em ambiente de desenvolvimento."""
    return (
        ENV in {"development", "test", "testing"}
        and isinstance(auth_handler.provider, MockAuthProvider)
        and os.getenv("AGHU_PROVIDER_TYPE", "").upper() == "SIMULADO"
    )


CAMPOS_LAUDO = {
    "MACROSCOPIA": ("laudo_macroscopico",),
    "CONGELACAO": ("resultado",),
    "MICROSCOPIA": ("diagnostico",),
    "REVISAO": ("diagnostico",),
    "IHQ": ("resultado",),
}


async def fila_revisoes(provider: SolicitacaoProviderInterface, limite: int, deslocamento: int) -> List[Dict[str, Any]]:
    """Retorna rascunhos e pré-laudos aguardando revisão do patologista."""
    itens = await provider.listar_revisoes(limite, deslocamento)
    for item in itens:
        item.pop("dados", None)  # conteúdo clínico não é necessário na listagem
        item["urgente"] = bool(item.get("urgente"))
    return itens


async def consultar_laudos(solicitacao_id: int, provider: SolicitacaoProviderInterface) -> Dict[str, Any]:
    """Expõe somente laudos de fases concluídas; pré-laudos não são laudos liberados."""
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    liberacao = await provider.buscar_liberacao(solicitacao_id)
    registros = await provider.listar_laudos_fases(solicitacao_id)
    documentos: List[Dict[str, Any]] = []
    if liberacao:
        for registro in registros:
            etapa = registro["etapa"]
            campos = CAMPOS_LAUDO.get(etapa, ())
            dados = registro["dados"]
            for campo in campos:
                valor = dados.get(campo)
                if isinstance(valor, str) and valor.strip():
                    documentos.append({
                        "fase": etapa, "tipo": campo, "conteudo": valor,
                        "validado_por": registro["concluido_por"], "validado_em": registro["concluido_em"],
                    })
    estado = (
        "ARQUIVADO" if solicitacao["status"] == STATUS_ARQUIVADO
        else "LIBERADO" if liberacao else "VALIDADO_PENDENTE_AGHU"
        if solicitacao["status"] == STATUS_AGUARDANDO_LIBERACAO else "EM_ANDAMENTO"
    )
    return {
        "solicitacao_id": solicitacao_id, "estado": estado,
        "liberacao": liberacao, "documentos": documentos,
        "aviso": "Textos locais de demonstração; nenhum PDF oficial do AGHU foi importado ou gerado.",
    }


async def simular_liberacao(
    solicitacao_id: int, usuario: Dict[str, Any], ip: Optional[str], provider: SolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Simula evento AGHU apenas em ambiente de testes com provedor de identidade Mock."""
    _exigir_perfil(usuario, {PERFIL_PRECEPTORIA}, "registrar a liberação do laudo")
    if not _demo_habilitada():
        raise HTTPException(403, "Liberação fictícia permitida somente com AGHU simulado em modo de demonstração")
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    if solicitacao["status"] != STATUS_AGUARDANDO_LIBERACAO or solicitacao["etapa_atual"] != STATUS_AGUARDANDO_LIBERACAO:
        raise HTTPException(409, "Finalize a revisão clínica antes de registrar a liberação")
    if await provider.buscar_liberacao(solicitacao_id):
        raise HTTPException(409, "Já existe um evento de liberação nesta solicitação")
    await _exigir_sem_pendencias(provider, solicitacao_id)
    agora = _agora()
    referencia = f"DEMO-AGHU-{solicitacao_id}"  # identificador artificial, nunca número de laudo oficial
    try:
        await provider.registrar_liberacao(solicitacao_id, "DEMONSTRACAO", referencia, agora, _login(usuario))
        await provider.atualizar_etapa(solicitacao_id, STATUS_AGUARDANDO_LIBERACAO, STATUS_LAUDO_LIBERADO, agora)
        await provider.inserir_movimentacao({
            "solicitacao_id": solicitacao_id, "tipo": "LIBERACAO_DEMO",
            "etapa_origem": STATUS_AGUARDANDO_LIBERACAO, "etapa_destino": STATUS_AGUARDANDO_LIBERACAO,
            "motivo": "Evento fictício de liberação do AGHU (somente demonstração)",
            "usuario": _login(usuario), "agora": agora,
        })
        await _gravar(provider, usuario=usuario, ip=ip, acao="LIBERACAO_DEMO_AGHU", solicitacao_id=solicitacao_id,
                      anteriores={"status": STATUS_AGUARDANDO_LIBERACAO},
                      novos={"status": STATUS_LAUDO_LIBERADO, "referencia_demonstracao": referencia})
        await provider.commit()
    except Exception as exc:
        await provider.rollback()
        logger.error("Falha em LIBERACAO_DEMO: %s", type(exc).__name__)
        raise
    return await consultar_laudos(solicitacao_id, provider)


async def arquivar_solicitacao(
    solicitacao_id: int, usuario: Dict[str, Any], ip: Optional[str], provider: SolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Arquiva apenas uma solicitação cujo evento de liberação já foi confirmado."""
    _exigir_perfil(usuario, {PERFIL_PRECEPTORIA}, "arquivar a solicitação")
    if not _demo_habilitada():
        raise HTTPException(403, "Arquivamento de demonstração desativado sem AGHU simulado")
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    if solicitacao["status"] != STATUS_LAUDO_LIBERADO or solicitacao["etapa_atual"] != STATUS_AGUARDANDO_LIBERACAO:
        raise HTTPException(409, "A solicitação precisa estar liberada antes de ser arquivada")
    liberacao = await provider.buscar_liberacao(solicitacao_id)
    if not liberacao or liberacao.get("arquivado_em"):
        raise HTTPException(409, "Evento de liberação inexistente ou solicitação já arquivada")
    await _exigir_sem_pendencias(provider, solicitacao_id)
    agora = _agora()
    try:
        await provider.arquivar_liberacao(solicitacao_id, agora, _login(usuario))
        await provider.atualizar_etapa(solicitacao_id, "ARQUIVO", STATUS_ARQUIVADO, agora)
        await provider.inserir_movimentacao({
            "solicitacao_id": solicitacao_id, "tipo": "ARQUIVAMENTO",
            "etapa_origem": STATUS_AGUARDANDO_LIBERACAO, "etapa_destino": "ARQUIVO",
            "motivo": "Arquivamento após confirmação de evento de liberação",
            "usuario": _login(usuario), "agora": agora,
        })
        await _gravar(provider, usuario=usuario, ip=ip, acao="ARQUIVAR_SOLICITACAO", solicitacao_id=solicitacao_id,
                      anteriores={"status": STATUS_LAUDO_LIBERADO},
                      novos={"status": STATUS_ARQUIVADO, "arquivado_em": agora})
        await provider.commit()
    except Exception as exc:
        await provider.rollback()
        logger.error("Falha em ARQUIVAMENTO: %s", type(exc).__name__)
        raise
    return await consultar_laudos(solicitacao_id, provider)
