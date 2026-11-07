# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    npm ci --strict-ssl=true
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements*.txt ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    python -m pip install --no-cache-dir -r requirements.txt && \
    python -m pip install --no-cache-dir -r requirements-cpu.txt
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
RUN python -c "import torch, rasterio, pyproj, numpy"
COPY backend/ backend/
COPY ml/ ml/
COPY scripts/ scripts/
COPY data/sample-sources.json data/sample-sources.json
COPY alembic.ini ./
COPY --from=web /web/dist frontend/dist
RUN useradd --uid 10001 --create-home terrasense && mkdir -p data artifacts && chown -R terrasense:terrasense /app && chmod -R a+rX /app
USER terrasense
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["python", "-m", "scripts.serve_container"]
