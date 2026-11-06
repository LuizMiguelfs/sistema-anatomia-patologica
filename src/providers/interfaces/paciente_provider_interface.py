from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PacienteProviderInterface(ABC):
    """
    Interface (contrato) para provedores de dados de pacientes.

    Formato padrão de um paciente retornado por qualquer provedor (dicionário):
        codigo (int), nome (str), dt_nascimento (date | None), sexo, cor,
        nome_mae, nome_pai, cpf, cns (str | None).

    Provedores NÃO aplicam regras de negócio (validação de CPF, duplicidade,
    permissões): isso é responsabilidade do controller.
    """

    #: Identificador da fonte de dados (ex.: "CSV", "POSTGRES").
    fonte: str = ""

    @abstractmethod
    def capacidades(self) -> Dict[str, bool]:
        """Informa o que a fonte suporta: {"escrita": bool, "exclusao": bool}."""

    @abstractmethod
    async def listar_pacientes(
        self, termo: Optional[str] = None, limite: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lista pacientes ativos ordenados por nome, com paginação.
        Se `termo` for numérico, busca por código (e CPF/CNS, quando a fonte tiver);
        caso contrário, busca por trecho do nome.
        """

    @abstractmethod
    async def obter_paciente_por_codigo(self, codigo: int) -> Optional[Dict[str, Any]]:
        """Retorna o paciente ativo com o código informado, ou None se não existir."""

    @abstractmethod
    async def existe_cpf(self, cpf: str, ignorar_codigo: Optional[int] = None) -> bool:
        """Indica se já existe paciente ativo com o CPF (somente dígitos), exceto `ignorar_codigo`."""

    @abstractmethod
    async def criar_paciente(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um paciente e retorna o registro criado (com o código gerado)."""

    @abstractmethod
    async def atualizar_paciente(self, codigo: int, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualiza o paciente e retorna o registro atualizado, ou None se não existir."""

    @abstractmethod
    async def excluir_paciente(self, codigo: int) -> Optional[Dict[str, Any]]:
        """
        Exclusão LÓGICA (soft delete): marca o registro como excluído sem apagá-lo.
        Retorna o registro marcado, ou None se não existir.
        """
