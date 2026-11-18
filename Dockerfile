# ============================
# 1. FRONTEND - BUILD (VUE 3)
# ============================
FROM node:20 AS frontend-build
WORKDIR /app

# Copia estrutura para o build do frontend gerar arquivos em /src/static/dist
COPY src ./src
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY frontend ./frontend
RUN cd frontend && npm run build

# ============================
# 2. BACKEND & RUNTIME FINAL
# ============================
FROM python:3.13-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

# Dependências do sistema necessárias para LDAP/AD, PostgreSQL e compilação de pacotes
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libpq-dev \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependências do Python nas versões travadas do uv.lock (as mesmas do CI)
RUN pip install --no-cache-dir uv==0.11.32
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Código do backend, migrações, scripts e dados fictícios de desenvolvimento
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts
COPY data/aghu_simulado.json data/pacientes.csv ./data/

# Copia o build estático do frontend gerado no estágio 1
COPY --from=frontend-build /app/src/static/dist ./src/static/dist

EXPOSE 8000

# Migrações + (opcional) carga de demonstração + servidor na porta de PORT (padrão 8000)
CMD ["sh", "scripts/iniciar.sh"]
