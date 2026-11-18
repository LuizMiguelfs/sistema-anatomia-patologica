"""Os templates SQL de cada provider apontam para o banco certo (solicitações no SQLite, AGHU no Postgres)."""
from pathlib import Path

SQL = Path(__file__).resolve().parent.parent / "src" / "providers" / "sql"


def test_sql_de_solicitacoes_nao_consulta_o_aghu():
    arquivos = sorted((SQL / "solicitacao").glob("*.sql"))
    assert arquivos, "pasta de SQL das solicitações vazia ou com outro nome"
    for arquivo in arquivos:
        assert "agh." not in arquivo.read_text(encoding="utf-8").lower(), arquivo.name


def test_sql_do_aghu_so_le_tabelas_do_aghu():
    for arquivo in (SQL / "aghu").glob("*.sql"):
        texto = arquivo.read_text(encoding="utf-8").lower()
        assert "from agh." in texto and "solicitacoes_exame" not in texto, arquivo.name
        assert not any(cmd in texto for cmd in ("insert ", "update ", "delete ")), arquivo.name
