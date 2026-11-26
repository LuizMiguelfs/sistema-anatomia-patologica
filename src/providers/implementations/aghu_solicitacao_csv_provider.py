"""Provider de solicitações do AGHU lido do CSV exportado da view ``vw_solicitacao``.

Dependência ativa: CSV autorizado pelo setor ou amostra anonimizada com o mesmo leiaute.
O arquivo é **apenas lido** (RN-01 / RNF005) e nunca deve ir para o Git (contém prontuário e
dados clínicos). Fica proibido em produção, que exige o AGHU real (``src/config.py``).

O agrupamento por solicitação, o tipo do exame, o status e o ID de cada amostra são definidos
em ``src/helpers/aghu_csv_helper.py``. O arquivo é lido uma vez e relido só se mudar no disco.
"""
import asyncio
import csv
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from ...helpers.aghu_csv_helper import STATUS_CANCELADO, agrupar_solicitacoes, colunas_ausentes
from ..interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface

#: Cache por caminho: (mtime_ns, tamanho) -> índice das solicitações.
_CACHE: Dict[str, Tuple[Tuple[int, int], Dict[str, Any]]] = {}
_TRAVA = threading.Lock()


def _assinatura(caminho: str) -> Tuple[int, int]:
    """Data de modificação e tamanho do arquivo, para saber se ele mudou."""
    info = os.stat(caminho)
    return info.st_mtime_ns, info.st_size


def carregar_csv(caminho: str) -> Dict[str, Any]:
    """Lê, valida o leiaute e agrupa o CSV (com cache enquanto o arquivo não mudar).

    Levanta ``RuntimeError`` (sem dados do arquivo na mensagem) se o arquivo não existir ou se
    faltarem colunas do leiaute da ``vw_solicitacao``.
    """
    caminho = os.path.abspath(caminho)
    if not os.path.isfile(caminho):
        raise RuntimeError("Arquivo CSV do AGHU não encontrado. Confira AGHU_CSV_PATH.")
    with _TRAVA:
        assinatura = _assinatura(caminho)
        guardado = _CACHE.get(caminho)
        if guardado and guardado[0] == assinatura:
            return guardado[1]
        # utf-8-sig aceita o BOM que planilhas costumam gravar; newline="" preserva campos com quebra de linha.
        with open(caminho, mode="r", encoding="utf-8-sig", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            faltando = colunas_ausentes(leitor.fieldnames)
            if faltando:
                raise RuntimeError(f"CSV do AGHU fora do leiaute da vw_solicitacao. Colunas ausentes: {', '.join(faltando)}")
            indice = agrupar_solicitacoes(leitor)
        _CACHE[caminho] = (assinatura, indice)
        return indice


class AghuSolicitacaoCsvProvider(AghuSolicitacaoProviderInterface):
    """Solicitações do AGHU a partir do CSV da ``vw_solicitacao`` (somente leitura)."""

    def __init__(self, caminho: str) -> None:
        """Recebe o caminho do CSV (``AGHU_CSV_PATH``)."""
        self.caminho = caminho

    async def _indice(self) -> Dict[str, Any]:
        """Índice das solicitações, lido em thread para não bloquear o event loop."""
        return await asyncio.to_thread(carregar_csv, self.caminho)

    async def _solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Solicitação agrupada (cabeçalho + todas as amostras da Anatomia), ou None."""
        indice = await self._indice()
        numero = str(solicitacao_aghu).strip()
        return indice["solicitacoes"].get(str(int(numero)) if numero.isdigit() else numero)

    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Cabeçalho: paciente, tipo (None se houver pendência), origem, status, data e pendências."""
        solicitacao = await self._solicitacao(solicitacao_aghu)
        if not solicitacao:
            return None
        return {
            chave: (list(valor) if isinstance(valor, list) else valor)
            for chave, valor in solicitacao.items() if chave != "amostras"
        }

    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        """Amostras vigentes destinadas à Anatomia (sem as canceladas no AGHU), com ID, código e descrição."""
        solicitacao = await self._solicitacao(solicitacao_aghu)
        if not solicitacao:
            return []
        return [dict(a) for a in solicitacao["amostras"] if a["status"] != STATUS_CANCELADO]

    async def listar_numeros(self) -> List[str]:
        """Números de todas as solicitações da Anatomia presentes no CSV."""
        return list((await self._indice())["solicitacoes"].keys())

    async def resumo(self) -> Dict[str, Any]:
        """Contagens do arquivo (sem dados de paciente), para conferir o CSV antes do uso."""
        indice = await self._indice()
        solicitacoes = indice["solicitacoes"].values()
        por_pendencia: Dict[str, int] = {}
        por_tipo: Dict[str, int] = {}
        for s in solicitacoes:
            for pendencia in s["pendencias"]:
                por_pendencia[pendencia] = por_pendencia.get(pendencia, 0) + 1
            if s["tipo_exame"]:
                por_tipo[s["tipo_exame"]] = por_tipo.get(s["tipo_exame"], 0) + 1
        return {
            "solicitacoes": len(indice["solicitacoes"]),
            "amostras": sum(len(s["amostras"]) for s in solicitacoes),
            "por_tipo": dict(sorted(por_tipo.items())),
            "com_pendencia": sum(1 for s in solicitacoes if s["pendencias"]),
            "por_pendencia": dict(sorted(por_pendencia.items())),
            "linhas_invalidas": indice["linhas_invalidas"],
            "linhas_fora_da_anatomia": indice["linhas_fora_da_anatomia"],
        }
