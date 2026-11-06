"""Carregamento centralizado de consultas SQL estáticas.

Use parâmetros vinculados SQLAlchemy (:nome), nunca concatenação de input de usuários.
"""
from pathlib import Path
from sqlalchemy import TextClause, text

SQL_ROOT = (Path(__file__).resolve().parents[1] / "providers" / "sql").resolve()


def read_sql_file(file_path: str) -> str:
    """Lê consulta existente; caminhos relativos são resolvidos a partir da raiz do projeto."""
    path = Path(file_path)
    if not path.is_absolute():
        path = (Path(__file__).resolve().parents[2] / path).resolve()
    return path.read_text(encoding="utf-8")


def load_provider_query(relative_path: str) -> TextClause:
    """Carrega uma consulta dentro de providers/sql como SQLAlchemy TextClause."""
    path = (SQL_ROOT / relative_path).resolve()
    if not path.is_relative_to(SQL_ROOT) or path.suffix.lower() != '.sql':
        raise ValueError("Consulta SQL fora do diretório permitido")
    return text(path.read_text(encoding="utf-8"))


def create_query(sql_content: str, params: dict) -> str:
    """Compatibilidade legada: apenas placeholders #chave estáticos.

    NÃO use para valores recebidos da API. Prefira text(sql).bindparams(**params).
    """
    for key, value in params.items():
        sql_content = sql_content.replace(f"#{key}", str(value))
    return sql_content
