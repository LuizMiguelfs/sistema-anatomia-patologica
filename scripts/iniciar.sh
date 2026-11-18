#!/bin/sh
# Inicialização do container (Dockerfile): migrações, carga de demonstração opcional e servidor.
# A porta vem de PORT (o Render define a dela); sem PORT, usa 8000.
set -e

# No Render, o login só aceita a origem do próprio site: o endereço público vem de RENDER_EXTERNAL_URL
# (https), mas atrás do proxy do Render o servidor se vê em http. Sem ALLOWED_ORIGINS, usa esse endereço.
if [ -z "${ALLOWED_ORIGINS:-}" ] && [ -n "${RENDER_EXTERNAL_URL:-}" ]; then
    export ALLOWED_ORIGINS="$RENDER_EXTERNAL_URL"
fi

echo "Aplicando migrações do banco local..."
alembic upgrade head

# Só para a demonstração (render.yaml liga CARGA_DEMONSTRACAO=true): dados e usuários fictícios.
# O próprio script recusa produção, AGHU real e banco que já tem solicitações.
if [ "${CARGA_DEMONSTRACAO:-false}" = "true" ]; then
    echo "Carregando dados fictícios de demonstração..."
    python -m scripts.seed_mvp --confirm || echo "Carga de demonstração não aplicada (veja a mensagem acima)."
fi

exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
