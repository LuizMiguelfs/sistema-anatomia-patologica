"""Os templates SQL de cada provider apontam para o banco certo (casos no SQLite, AGHU no Postgres)."""
from pathlib import Path

SQL = Path(__file__).resolve().parent.parent / "src" / "providers" / "sql"


def test_sql_de_casos_nao_consulta_o_aghu():
    for arquivo in (SQL / "caso").glob("*.sql"):
        assert "agh." not in arquivo.read_text(encoding="utf-8").lower(), arquivo.name


def test_sql_do_aghu_so_le_tabelas_do_aghu():
    for arquivo in (SQL / "aghu").glob("*.sql"):
        texto = arquivo.read_text(encoding="utf-8").lower()
        assert "from agh." in texto and "casos" not in texto, arquivo.name
        assert not any(cmd in texto for cmd in ("insert ", "update ", "delete ")), arquivo.name
