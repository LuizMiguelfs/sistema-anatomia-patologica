# Deploy para Render (MODO DEMONSTRAÇÃO COM DADOS SINTÉTICOS)
FROM node:20-bookworm AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libpq-dev libsasl2-dev libldap2-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts
COPY data/pacientes.csv ./data/pacientes.csv
COPY data/aghu_simulado.json ./data/aghu_simulado.json
COPY --from=frontend-build /app/src/static/dist ./src/static/dist
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/data
EXPOSE 10000
CMD ["/app/docker-entrypoint.sh"]
