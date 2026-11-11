"""Provider SIMULADO do AGHU para solicitações de exame (desenvolvimento e demonstração).

Lê um arquivo JSON de solicitações FICTÍCIAS, no mesmo formato que o provider PostgreSQL
devolve (cabeçalho + amostras). Somente leitura, como o AGHU real (RNF005). Nunca é usado
em produção: `src/config.py` exige o AGHU real (POSTGRES) quando ENV=production.

Formato de cada item do JSON:
    {"solicitacao_aghu": 900001, "paciente_codigo_aghu": 5001, "paciente_nome": "...",
     "prontuario_aghu": "10000001", "tipo_exame": "HP", "urgente": false,
     "amostras": [{"amostra_aghu": 1, "descricao": "..."}]}
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface


@lru_cache(maxsize=4)
def _carregar(caminho: str) -> Dict[str, Dict[str, Any]]:
    """Lê o JSON uma vez e indexa pelo número da solicitação (texto)."""
    path = Path(caminho)
    if not path.exists():
        return {}
    itens = json.loads(path.read_text(encoding="utf-8"))
    return {str(item["solicitacao_aghu"]): item for item in itens}


class AghuSolicitacaoSimuladoProvider(AghuSolicitacaoProviderInterface):
    """Consulta solicitações fictícias em arquivo JSON (somente leitura)."""

    def __init__(self, caminho: str) -> None:
        """Recebe o caminho do arquivo JSON de solicitações fictícias."""
        self.caminho = caminho

    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Cabeçalho da solicitação fictícia, ou None."""
        item = _carregar(self.caminho).get(str(solicitacao_aghu).strip())
        if not item:
            return None
        return {chave: valor for chave, valor in item.items() if chave != "amostras"}

    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        """Amostras da solicitação fictícia."""
        item = _carregar(self.caminho).get(str(solicitacao_aghu).strip())
        return list(item.get("amostras", [])) if item else []

    def listar_numeros(self) -> List[str]:
        """Números de todas as solicitações fictícias (usado pelo script de carga da demonstração)."""
        return list(_carregar(self.caminho).keys())
