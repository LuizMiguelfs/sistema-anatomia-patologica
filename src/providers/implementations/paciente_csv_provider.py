import asyncio
import csv
import os
import re
import tempfile
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from ...helpers.string_helper import normalizar_para_busca, somente_digitos
from ..interfaces.paciente_provider_interface import PacienteProviderInterface

# Colunas mínimas mantidas pelo provedor. Colunas extras já existentes no arquivo
# (ex.: especialidade, procedimento) são preservadas ao regravar.
COLUNAS_PADRAO = [
    "codigo", "nome", "dt_nascimento", "cpf", "cns", "sexo", "cor",
    "nome_mae", "nome_pai", "deleted_at",
]
CAMPOS_EDITAVEIS = ["nome", "dt_nascimento", "cpf", "cns", "sexo", "cor", "nome_mae", "nome_pai"]
VALORES_NULOS = {"", "(null)", "null", "none"}
TERMO_NUMERICO = re.compile(r"\d[\d.\-\s]*")

# Um lock por arquivo evita que duas requisições simultâneas sobrescrevam a escrita uma da outra.
_locks: Dict[str, asyncio.Lock] = {}


def _lock_para(caminho: str) -> asyncio.Lock:
    """Retorna o lock associado ao caminho absoluto do CSV."""
    chave = os.path.abspath(caminho)
    if chave not in _locks:
        _locks[chave] = asyncio.Lock()
    return _locks[chave]


def _valor(row: Dict[str, Any], campo: str) -> Optional[str]:
    """Lê um campo do CSV tratando '(null)' e vazio como None."""
    valor = row.get(campo)
    if valor is None:
        return None
    valor = str(valor).strip()
    return None if valor.lower() in VALORES_NULOS else valor


def _para_csv(valor: Any) -> str:
    """Converte um valor Python para o texto gravado no CSV."""
    if valor is None:
        return ""
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return str(valor)


class PacienteCsvProvider(PacienteProviderInterface):
    """
    Provedor de pacientes baseado em arquivo CSV (desenvolvimento offline).
    Suporta CRUD completo com exclusão LÓGICA (coluna `deleted_at`) e gravação atômica.
    """

    fonte = "CSV"

    def __init__(self, csv_path: str = "data/pacientes.csv"):
        """Recebe o caminho do CSV e garante que o arquivo exista."""
        self.csv_path = csv_path
        self._check_file_exists()

    def _check_file_exists(self) -> None:
        """Falha cedo, com mensagem clara, se o arquivo não existir."""
        if not os.path.isfile(self.csv_path):
            raise RuntimeError(f"Arquivo CSV de pacientes não encontrado em: {self.csv_path}")

    def capacidades(self) -> Dict[str, bool]:
        """CSV suporta escrita e exclusão lógica."""
        return {"escrita": True, "exclusao": True}

    # ------------------------------------------------------------------ I/O
    def _ler_sync(self) -> tuple[List[str], List[Dict[str, Any]]]:
        """Lê o CSV inteiro: (cabeçalho, linhas)."""
        with open(self.csv_path, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            linhas = list(reader)
            cabecalho = list(reader.fieldnames or [])
        for coluna in COLUNAS_PADRAO:
            if coluna not in cabecalho:
                cabecalho.append(coluna)
        return cabecalho, linhas

    def _gravar_sync(self, cabecalho: List[str], linhas: List[Dict[str, Any]]) -> None:
        """Grava o CSV de forma atômica (arquivo temporário + rename)."""
        diretorio = os.path.dirname(os.path.abspath(self.csv_path))
        fd, tmp_path = tempfile.mkstemp(prefix=".pacientes-", suffix=".csv", dir=diretorio)
        try:
            with os.fdopen(fd, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cabecalho, extrasaction="ignore")
                writer.writeheader()
                for linha in linhas:
                    writer.writerow({c: linha.get(c, "") or "" for c in cabecalho})
            os.replace(tmp_path, self.csv_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    async def _ler(self) -> tuple[List[str], List[Dict[str, Any]]]:
        """Leitura em thread para não bloquear o event loop."""
        return await asyncio.to_thread(self._ler_sync)

    async def _gravar(self, cabecalho: List[str], linhas: List[Dict[str, Any]]) -> None:
        """Gravação em thread para não bloquear o event loop."""
        await asyncio.to_thread(self._gravar_sync, cabecalho, linhas)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _codigo(row: Dict[str, Any]) -> Optional[int]:
        """Converte o código da linha para int (None se inválido)."""
        try:
            return int(str(row.get("codigo", "")).strip())
        except ValueError:
            return None

    @staticmethod
    def _ativo(row: Dict[str, Any]) -> bool:
        """Linha não excluída logicamente."""
        return _valor(row, "deleted_at") is None

    @classmethod
    def _normalizar(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        """Converte uma linha do CSV para o formato padrão de paciente da interface."""
        dt_txt = _valor(row, "dt_nascimento")
        try:
            dt_nascimento = date.fromisoformat(dt_txt[:10]) if dt_txt else None
        except ValueError:
            dt_nascimento = None
        return {
            "codigo": cls._codigo(row),
            "nome": _valor(row, "nome") or "",
            "dt_nascimento": dt_nascimento,
            "sexo": _valor(row, "sexo"),
            "cor": _valor(row, "cor"),
            "nome_mae": _valor(row, "nome_mae"),
            "nome_pai": _valor(row, "nome_pai"),
            "cpf": _valor(row, "cpf"),
            "cns": _valor(row, "cns"),
        }

    def _localizar(self, linhas: List[Dict[str, Any]], codigo: int) -> Optional[Dict[str, Any]]:
        """Encontra a linha ativa com o código informado."""
        for row in linhas:
            if self._codigo(row) == codigo and self._ativo(row):
                return row
        return None

    # ---------------------------------------------------------- consultas
    async def listar_pacientes(
        self, termo: Optional[str] = None, limite: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Lista pacientes ativos; termo numérico busca código/CPF/CNS, texto busca nome (sem acento)."""
        _, linhas = await self._ler()
        ativos = [r for r in linhas if self._ativo(r) and self._codigo(r) is not None]

        termo = (termo or "").strip()
        if termo:
            if TERMO_NUMERICO.fullmatch(termo):
                # Código exato, ou trecho de CPF/CNS (aceita pontuação: 111.111.111-11)
                digitos = somente_digitos(termo)
                ativos = [
                    r for r in ativos
                    if str(self._codigo(r)) == digitos
                    or digitos in somente_digitos(_valor(r, "cpf"))
                    or digitos in somente_digitos(_valor(r, "cns"))
                ]
            else:
                alvo = normalizar_para_busca(termo)
                ativos = [r for r in ativos if alvo in normalizar_para_busca(_valor(r, "nome"))]

        ativos.sort(key=lambda r: (normalizar_para_busca(_valor(r, "nome")), self._codigo(r)))
        return [self._normalizar(r) for r in ativos[offset: offset + limite]]

    async def obter_paciente_por_codigo(self, codigo: int) -> Optional[Dict[str, Any]]:
        """Busca um paciente ativo pelo código."""
        _, linhas = await self._ler()
        row = self._localizar(linhas, codigo)
        return self._normalizar(row) if row else None

    async def existe_cpf(self, cpf: str, ignorar_codigo: Optional[int] = None) -> bool:
        """Verifica duplicidade de CPF entre pacientes ativos."""
        alvo = somente_digitos(cpf)
        if not alvo:
            return False
        _, linhas = await self._ler()
        return any(
            self._ativo(r)
            and self._codigo(r) != ignorar_codigo
            and somente_digitos(_valor(r, "cpf")) == alvo
            for r in linhas
        )

    # ------------------------------------------------------------ escrita
    async def criar_paciente(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um paciente com código sequencial (maior código existente + 1, incluindo excluídos)."""
        async with _lock_para(self.csv_path):
            cabecalho, linhas = await self._ler()
            codigos = [c for c in (self._codigo(r) for r in linhas) if c is not None]
            novo = {c: "" for c in cabecalho}
            novo["codigo"] = str(max(codigos, default=0) + 1)
            for campo in CAMPOS_EDITAVEIS:
                novo[campo] = _para_csv(dados.get(campo))
            linhas.append(novo)
            await self._gravar(cabecalho, linhas)
            return self._normalizar(novo)

    async def atualizar_paciente(self, codigo: int, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualiza os campos editáveis de um paciente ativo."""
        async with _lock_para(self.csv_path):
            cabecalho, linhas = await self._ler()
            row = self._localizar(linhas, codigo)
            if row is None:
                return None
            for campo in CAMPOS_EDITAVEIS:
                row[campo] = _para_csv(dados.get(campo))
            await self._gravar(cabecalho, linhas)
            return self._normalizar(row)

    async def excluir_paciente(self, codigo: int) -> Optional[Dict[str, Any]]:
        """Exclusão lógica: preenche `deleted_at`; a linha permanece no arquivo."""
        async with _lock_para(self.csv_path):
            cabecalho, linhas = await self._ler()
            row = self._localizar(linhas, codigo)
            if row is None:
                return None
            registro = self._normalizar(row)
            row["deleted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            await self._gravar(cabecalho, linhas)
            return registro
