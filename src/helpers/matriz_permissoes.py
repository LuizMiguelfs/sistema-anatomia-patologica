"""Matriz inicial de permissões do SAP para revisão com o HC-UFPE (T05).

As permissões do formulário vêm da mesma definição usada pela API (FASES), evitando
uma segunda matriz inconsistente no frontend. Qualquer mutação exige verificação no servidor.
"""
from typing import Any, Dict

from .formularios_fase import FASES

PERFIS = ("RECEPCAO", "LABORATORIO", "RESIDENTE", "PRECEPTORIA", "CHEFIA")
TODOS = set(PERFIS)


def matriz_inicial() -> Dict[str, Any]:
    """Descreve o contrato inicial; não substitui a homologação da Chefia/Preceptoria."""
    return {
        "versao": "inicial-2026-11-25",
        "homologada_pelo_hc": False,
        "consulta": list(PERFIS),
        "retirada_credencial": ["RECEPCAO"],
        "desfazer_retirada_credencial": ["RECEPCAO"],
        "liberar_laudo": ["PRECEPTORIA"],
        "arquivar": ["PRECEPTORIA"],
        "configuracoes": ["CHEFIA"],
        "fases": {
            f["etapa"]: {
                "consultar": list(PERFIS),
                "editar": list(f["salvar"]),
                "concluir": list(f["concluir"]),
                "campos_restritos": {c["nome"]: list(c["perfis"]) for c in f["campos"] if "perfis" in c},
            }
            for f in FASES
        },
        "observacao": "Estação autenticada e ator que confirma a retirada podem ser pessoas diferentes; a ação usa o perfil da credencial confirmada.",
    }


def capacidades_do_perfil(perfil: str) -> Dict[str, Any]:
    """Retorna ações atribuídas ao perfil local ativo na sessão."""
    p = str(perfil or "").upper()
    m = matriz_inicial()
    return {
        "perfil": p,
        "pode_consultar": p in m["consulta"],
        "pode_confirmar_retirada": p in m["retirada_credencial"],
        "pode_liberar_laudo": p in m["liberar_laudo"],
        "pode_arquivar": p in m["arquivar"],
        "fases": {
            etapa: {
                "pode_consultar": p in regras["consultar"],
                "pode_editar": p in regras["editar"],
                "pode_concluir": p in regras["concluir"],
            }
            for etapa, regras in m["fases"].items()
        },
    }
