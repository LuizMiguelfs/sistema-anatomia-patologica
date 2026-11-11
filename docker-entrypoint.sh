#!/bin/sh
set -eu
cd /app

mkdir -p /app/data

# Restrição de origem para o próprio domínio Render (mesma origem da SPA/API).
if [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ] && [ -z "${ALLOWED_ORIGINS:-}" ]; then
  export ALLOWED_ORIGINS="https://${RENDER_EXTERNAL_HOSTNAME}"
fi

# Migrações no runtime: discos persistentes não são montados durante o build.
python -m alembic upgrade head

if [ "${DEMO_SEED:-false}" = "true" ]; then
  if [ "${ENV:-development}" = "production" ]; then
    echo "ERRO: DEMO_SEED não pode ser utilizado em produção." >&2
    exit 1
  fi
  # Seed apenas na primeira inicialização (pode ser repetido após hibernação no plano grátis).
  if python - <<'PYSEED'
import os, sqlite3, sys
from urllib.parse import urlparse
dsn = os.getenv("APP_DB_URL", "sqlite+aiosqlite:////app/data/app.db")
if not dsn.startswith("sqlite+aiosqlite:////"):
    print("DEMO_SEED requer SQLite com caminho absoluto", file=sys.stderr)
    sys.exit(2)
path = "/" + dsn.split("sqlite+aiosqlite:////", 1)[1]
with sqlite3.connect(path) as db:
    row = db.execute("SELECT COUNT(*) FROM casos").fetchone()
    sys.exit(0 if row and row[0] == 0 else 1)
PYSEED
  then
    echo "Carregando exclusivamente os dados sintéticos da demonstração..."
    python -m scripts.seed_mvp --confirm
  else
    echo "Banco já populado; mantendo dados existentes."
  fi
fi

exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-10000}"
