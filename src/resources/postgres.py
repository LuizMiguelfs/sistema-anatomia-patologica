"""Compatibilidade com o AGHU/PostgreSQL.

A conexão é gerenciada em src.main (lifespan) e entregue por dependência
FastAPI; não criamos engine global nem exigimos POSTGRES_DSN no import.
"""
from .database import get_aghu_db_session

get_postgres_session = get_aghu_db_session
