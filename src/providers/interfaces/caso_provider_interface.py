from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class CasoProviderInterface(ABC):
    """
    Interface (contrato) do acesso aos dados de casos no banco local da aplicação:
    casos, amostras, movimentações, pendências, fluxo configurável e numeração interna.

    Provedores NÃO aplicam regras de negócio e NÃO fazem commit nos métodos de escrita:
    o controller controla a transação (`commit`/`rollback`) para gravar caso, movimentação
    e auditoria juntos. `session` é a sessão usada pela auditoria na mesma transação.
    Datas são texto ISO 8601 (UTC). Filtros da busca: solicitacao, prontuario (exato),
    identificador, tipo_exame, etapa e status. Nome e prontuário do paciente entram e saem
    em claro; a implementação é responsável por gravá-los cifrados (AES-256).
    """

    session: AsyncSession

    @abstractmethod
    async def commit(self) -> None:
        """Confirma a transação."""

    @abstractmethod
    async def rollback(self) -> None:
        """Desfaz a transação."""

    @abstractmethod
    async def buscar_por_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Caso ativo da solicitação do AGHU (id e identificador interno), ou None."""

    @abstractmethod
    async def buscar_por_id(self, caso_id: int) -> Optional[Dict[str, Any]]:
        """Caso ativo pelo id, ou None."""

    @abstractmethod
    async def proximo_numero(self, sigla: str, ano: int) -> int:
        """Reserva o próximo número do identificador interno da sigla no ano."""

    @abstractmethod
    async def inserir_caso(self, dados: Dict[str, Any]) -> int:
        """Insere o caso e devolve o id."""

    @abstractmethod
    async def atualizar_dados_aghu(self, caso_id: int, nome: str, prontuario: Optional[str], agora: str) -> None:
        """Atualiza apenas o snapshot cadastral local (nome, prontuário e data de sincronização)."""

    @abstractmethod
    async def inserir_amostra(self, caso_id: int, amostra_aghu: str, descricao: Optional[str]) -> None:
        """Vincula uma amostra do AGHU ao caso."""

    @abstractmethod
    async def listar_amostras(self, caso_id: int) -> List[Dict[str, Any]]:
        """Amostras do caso."""

    @abstractmethod
    async def listar_casos(self, filtros: Dict[str, Any], limite: int, deslocamento: int) -> List[Dict[str, Any]]:
        """Página de casos ativos conforme os filtros (None = filtro desativado)."""

    @abstractmethod
    async def contar_casos(self, filtros: Dict[str, Any]) -> int:
        """Total de casos ativos conforme os filtros."""

    @abstractmethod
    async def atualizar_etapa(self, caso_id: int, etapa_atual: str, status: str, agora: str) -> None:
        """Atualiza etapa e status do caso."""

    @abstractmethod
    async def inserir_movimentacao(self, dados: Dict[str, Any]) -> None:
        """Registra uma movimentação (append-only)."""

    @abstractmethod
    async def listar_movimentacoes(self, caso_id: int) -> List[Dict[str, Any]]:
        """Linha do tempo das movimentações do caso."""

    @abstractmethod
    async def ultima_movimentacao_desvio(self, caso_id: int) -> Optional[Dict[str, Any]]:
        """Último encaminhamento ou retorno do caso, ou None."""

    @abstractmethod
    async def contar_pendencias_abertas(self, caso_id: int) -> int:
        """Quantidade de inconformidades abertas do caso."""

    @abstractmethod
    async def destinos(self, tipo_exame: str, etapa_origem: str, tipo: str) -> List[str]:
        """Etapas de destino permitidas pelo fluxo configurado (AVANCO ou ENCAMINHAMENTO)."""

    @abstractmethod
    async def etapa_inicial(self, tipo_exame: str) -> Optional[str]:
        """Primeira etapa do fluxo do tipo de exame, ou None se não configurado."""

    # --- MVP: Solicitações de Exames, retirada e formulários por fase ---------
    @abstractmethod
    async def listar_solicitacoes(self, filtros: Dict[str, Any], limite: int, deslocamento: int) -> List[Dict[str, Any]]:
        """Página de "Não retirados" ou "Retirados" (filtros: situacao, tipo_exame, de, ate, busca)."""

    @abstractmethod
    async def contar_solicitacoes(self, filtros: Dict[str, Any]) -> int:
        """Total de "Não retirados" ou "Retirados" conforme os filtros."""

    @abstractmethod
    async def listar_fila(
        self, etapa: str, filtros: Dict[str, Any], concluidas_desde: str, limite: int, deslocamento: int
    ) -> List[Dict[str, Any]]:
        """Fila da fase: pendentes da etapa e concluídas desde `concluidas_desde` (filtros: tipo_exame, busca)."""

    @abstractmethod
    async def contar_fila(self, etapa: str, filtros: Dict[str, Any], concluidas_desde: str) -> int:
        """Total da fila da fase."""

    @abstractmethod
    async def marcar_retirada(self, caso_id: int, etapa_atual: str, status: str, usuario: str, agora: str) -> None:
        """Registra a retirada da recepção e a nova etapa da solicitação."""

    @abstractmethod
    async def desfazer_retirada(self, caso_id: int, status: str, agora: str) -> None:
        """Desfaz a retirada: a solicitação volta à etapa RECEPCAO."""

    @abstractmethod
    async def buscar_fase(self, caso_id: int, etapa: str) -> Optional[Dict[str, Any]]:
        """Formulário da fase da solicitação (dados já decodificados do JSON), ou None."""

    @abstractmethod
    async def salvar_fase(self, dados: Dict[str, Any]) -> None:
        """Cria ou substitui o formulário da fase (caso_id, etapa, dados, situacao, usuario, agora, concluido_*)."""
