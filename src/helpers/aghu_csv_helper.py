"""Leitura do CSV exportado da view ``vw_solicitacao`` do AGHU (somente leitura, RN-01).

O CSV traz **uma linha por amostra** (item da solicitação). Este helper agrupa as linhas por
solicitação e identifica, para cada uma, o tipo de exame do SAP, a origem, o status, as datas e
as amostras destinadas à Anatomia Patológica, cada uma com ID próprio.

Regras (fail closed, ``docs/REFINO_POS_AVALIACAO.md``):

* Só entram as linhas dos laboratórios da Anatomia (``LABS_ANATOMIA``). Linhas de outros
  laboratórios não são amostras do SAP.
* O tipo do exame vem da sigla do AGHU (``SIGLA_PARA_TIPO``), nunca do nome do material nem
  de escolha manual. Amostras canceladas no AGHU não contam para o tipo.
* Se as amostras vigentes levam a tipos diferentes, ou se há sigla não mapeada, amostra
  repetida ou paciente divergente, a solicitação fica **sem tipo** (``tipo_exame = None``) e
  com a pendência listada. O controller então recusa a abertura (409). O SAP não escolhe
  o primeiro exame em silêncio.
* O ID de cada amostra é a chave da origem: ``<solicitação AGHU>-<número da amostra>``. A
  numeração do AGHU é mantida tal como vem, inclusive quando não é contínua (a view só traz
  os itens da Anatomia).

Os mapeamentos abaixo ainda **precisam ser validados pela Chefia do UACAP e pelo DBA/SETISD**
(ponto de decisão 1 e item 1 da seção 9 do REFINO). Mudá-los não exige mudar o código.
"""
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

#: Colunas exigidas no CSV (leiaute da view ``vw_solicitacao``). Colunas a mais são ignoradas.
COLUNAS_OBRIGATORIAS = (
    "codigo_solicitacao", "numero_amostra", "cod_status_item", "status_item_exame",
    "data_solicitacao", "nome_paciente", "prontuario", "especialidade", "convenio", "origem",
    "unidade", "codigo_lab", "sigla_exame", "nome_exame", "descricao_material",
)

#: Laboratórios executores da Anatomia Patológica no AGHU (``codigo_lab``). A VALIDAR com o DBA.
LABS_ANATOMIA = frozenset({"139", "203", "205", "207", "209"})

#: Sigla do exame no AGHU -> tipo de exame do SAP. A VALIDAR com a Chefia do UACAP.
SIGLA_PARA_TIPO: Dict[str, str] = {
    "APECR": "HP",   # Anatomopatológico - peça cirúrgica
    "HPDER": "HP",   # Histopatológico dermatologia
    "MBIOP": "HP",   # Anatomopatológico - mama (biópsia)
    "MPCIR": "HP",   # Anatomopatológico - mama (peça cirúrgica)
    "COLUT": "HP",   # Anatomopatológico - colo uterino
    "COUT2": "HP",   # Anatomopatológico - colo uterino
    "CONGE": "CO",   # Exame transoperatório de congelação
    "IMUHI": "IHQ",  # Imuno-histoquímica
    "CCVM": "CCV",   # Citopatológico cérvico-vaginal / microflora
    "CITOP": "CG",   # Citopatológico
    "CPMAM": "CG",   # Citopatológico de mama
    "CITO": "CG",    # Citologia oncótica (o doc. 00 a inclui em Citologia Geral)
}

#: Status do item no AGHU que tira a amostra do fluxo do SAP.
STATUS_CANCELADO = "CA"
#: Status resumido quando as amostras da solicitação estão em status diferentes no AGHU.
STATUS_MISTO = "MISTO"

# Pendências que bloqueiam a definição do tipo (e, portanto, a abertura no SAP).
PENDENCIA_TIPOS_CONFLITANTES = "TIPOS_CONFLITANTES"
PENDENCIA_SIGLA_NAO_MAPEADA = "SIGLA_NAO_MAPEADA"
PENDENCIA_AMOSTRA_DUPLICADA = "AMOSTRA_DUPLICADA"
PENDENCIA_PACIENTE_DIVERGENTE = "PACIENTE_DIVERGENTE"
PENDENCIA_SEM_AMOSTRA_VIGENTE = "SEM_AMOSTRA_VIGENTE"

_INVISIVEIS = re.compile("[​‌‍⁠﻿]")
_ESPACOS = re.compile(r"\s+")


def limpar(valor: Any) -> Optional[str]:
    """Tira caracteres invisíveis e espaços repetidos; devolve None para texto vazio."""
    texto = _ESPACOS.sub(" ", _INVISIVEIS.sub("", str(valor or ""))).strip()
    return texto or None


def inteiro(valor: Any) -> Optional[int]:
    """Converte um código numérico do AGHU para int (None se vazio ou inválido)."""
    texto = limpar(valor)
    return int(texto) if texto and texto.isdigit() else None


def data_iso(valor: Any) -> Optional[str]:
    """Converte ``dd/mm/aaaa`` (formato do AGHU) para ``aaaa-mm-dd``; None se inválida."""
    texto = limpar(valor)
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def id_amostra_aghu(solicitacao_aghu: Any, amostra_aghu: Any) -> str:
    """ID da amostra na origem: ``<solicitação AGHU>-<número da amostra>`` (ex.: ``800002-2``)."""
    return f"{str(solicitacao_aghu).strip()}-{str(amostra_aghu).strip()}"


def rotulo_amostra(identificador_interno: str, amostra_aghu: Any) -> str:
    """Rótulo da amostra no SAP: identificador interno + ``A`` + número do AGHU (ex.: ``HP-0001/26-A2``)."""
    return f"{identificador_interno}-A{str(amostra_aghu).strip()}"


def identificar_amostras(
    solicitacao: Dict[str, Any], amostras: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Acrescenta a cada amostra gravada no SAP o ID da origem (``id_aghu``) e o rótulo interno (``identificador``)."""
    return [
        {
            **amostra,
            "id_aghu": id_amostra_aghu(solicitacao["solicitacao_aghu"], amostra["amostra_aghu"]),
            "identificador": rotulo_amostra(solicitacao["identificador_interno"], amostra["amostra_aghu"]),
        }
        for amostra in amostras
    ]


def colunas_ausentes(colunas: Optional[Iterable[str]]) -> List[str]:
    """Colunas obrigatórias que não estão no cabeçalho do CSV (lista vazia se o leiaute confere)."""
    presentes = {limpar(coluna) for coluna in (colunas or [])}
    return [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in presentes]


def _amostra(linha: Dict[str, Any], solicitacao_aghu: int, numero: int) -> Dict[str, Any]:
    """Monta a amostra a partir de uma linha do CSV (sem dados do paciente)."""
    sigla = (limpar(linha.get("sigla_exame")) or "").upper() or None
    return {
        "id_amostra": id_amostra_aghu(solicitacao_aghu, numero),
        "amostra_aghu": numero,
        "codigo_exame": sigla,
        "nome_exame": limpar(linha.get("nome_exame")),
        "tipo_exame": SIGLA_PARA_TIPO.get(sigla or ""),
        "descricao": limpar(linha.get("descricao_material")),
        "status": (limpar(linha.get("cod_status_item")) or "").upper() or None,
        "status_descricao": limpar(linha.get("status_item_exame")),
        "codigo_lab": limpar(linha.get("codigo_lab")),
    }


def _cabecalho(linha: Dict[str, Any], solicitacao_aghu: int) -> Dict[str, Any]:
    """Dados da solicitação que se repetem em todas as linhas dela (vem da primeira linha)."""
    return {
        "solicitacao_aghu": solicitacao_aghu,
        # A view não traz o código do paciente; o vínculo técnico fica vazio até o DBA incluí-lo.
        "paciente_codigo_aghu": None,
        "paciente_nome": limpar(linha.get("nome_paciente")),
        "prontuario_aghu": limpar(linha.get("prontuario")),
        "data_solicitacao": data_iso(linha.get("data_solicitacao")),
        "origem": limpar(linha.get("origem")),
        "unidade": limpar(linha.get("unidade")),
        "especialidade": limpar(linha.get("especialidade")),
        "convenio": limpar(linha.get("convenio")),
    }


def _classificar(solicitacao: Dict[str, Any]) -> Dict[str, Any]:
    """Define tipo, urgência e status da solicitação a partir das amostras; registra pendências."""
    amostras: List[Dict[str, Any]] = solicitacao["amostras"]
    vigentes = [a for a in amostras if a["status"] != STATUS_CANCELADO]
    pendencias: List[str] = solicitacao["pendencias"]
    if any(a["tipo_exame"] is None for a in vigentes):
        pendencias.append(PENDENCIA_SIGLA_NAO_MAPEADA)
    tipos = sorted({a["tipo_exame"] for a in vigentes if a["tipo_exame"]})
    if len(tipos) > 1:
        pendencias.append(PENDENCIA_TIPOS_CONFLITANTES)
    if not vigentes:
        pendencias.append(PENDENCIA_SEM_AMOSTRA_VIGENTE)
    status = sorted({a["status"] for a in amostras if a["status"]})
    descricoes = {a["status"]: a["status_descricao"] for a in amostras}
    tipo = tipos[0] if len(tipos) == 1 and not pendencias else None
    solicitacao.update(
        {
            "tipo_exame": tipo,
            "tipos_exame": tipos,
            "urgente": "CO" in tipos,  # Congelação é sempre urgente (decisão do setor)
            "status_aghu": status[0] if len(status) == 1 else STATUS_MISTO,
            "status_descricao": descricoes.get(status[0]) if len(status) == 1 else "Amostras em status diferentes",
            "qtd_amostras": len(vigentes),
            "amostras_canceladas": len(amostras) - len(vigentes),
        }
    )
    return solicitacao


def agrupar_solicitacoes(linhas: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Agrupa as linhas do CSV por solicitação e classifica cada uma.

    Devolve ``{"solicitacoes": {"<número>": {...cabeçalho, "amostras": [...]}}, "linhas_invalidas": n,
    "linhas_fora_da_anatomia": n}``. As amostras vêm ordenadas pelo número do AGHU, incluindo as
    canceladas (com ``status = "CA"``); quem abre a solicitação usa só as vigentes.
    """
    solicitacoes: Dict[str, Dict[str, Any]] = {}
    invalidas = fora_da_anatomia = 0
    for linha in linhas:
        solicitacao_aghu = inteiro(linha.get("codigo_solicitacao"))
        numero = inteiro(linha.get("numero_amostra"))
        if solicitacao_aghu is None or numero is None:
            invalidas += 1
            continue
        if limpar(linha.get("codigo_lab")) not in LABS_ANATOMIA:
            fora_da_anatomia += 1
            continue
        chave = str(solicitacao_aghu)
        atual = solicitacoes.get(chave)
        if atual is None:
            atual = solicitacoes[chave] = {**_cabecalho(linha, solicitacao_aghu), "amostras": [], "pendencias": []}
        elif (limpar(linha.get("nome_paciente")), limpar(linha.get("prontuario"))) != (
            atual["paciente_nome"], atual["prontuario_aghu"]
        ) and PENDENCIA_PACIENTE_DIVERGENTE not in atual["pendencias"]:
            atual["pendencias"].append(PENDENCIA_PACIENTE_DIVERGENTE)
        if any(a["amostra_aghu"] == numero for a in atual["amostras"]):
            if PENDENCIA_AMOSTRA_DUPLICADA not in atual["pendencias"]:
                atual["pendencias"].append(PENDENCIA_AMOSTRA_DUPLICADA)
            continue
        atual["amostras"].append(_amostra(linha, solicitacao_aghu, numero))
    for solicitacao in solicitacoes.values():
        solicitacao["amostras"].sort(key=lambda amostra: amostra["amostra_aghu"])
        _classificar(solicitacao)
    return {
        "solicitacoes": solicitacoes,
        "linhas_invalidas": invalidas,
        "linhas_fora_da_anatomia": fora_da_anatomia,
    }
