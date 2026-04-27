FROM python:3.11-slim AS base

WORKDIR /app

# Dependencias do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias primeiro (cache de camadas)
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    ccxt \
    pydantic \
    structlog \
    && pip install --no-cache-dir -e .

# Copiar codigo
COPY packages/ packages/
COPY config/ config/
COPY scripts/ scripts/

# Porta da API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Rodar API
CMD ["uvicorn", "packages.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
