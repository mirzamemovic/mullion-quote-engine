# Production image (PLAN.md section 12): one process serves the API and the built frontend.
# Stage 1 builds the React app; stage 2 is the Python runtime with the system libraries
# WeasyPrint needs for PDFs (M7). Builds for amd64 and arm64 (the Oracle Ampere server).

FROM node:26-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv

# WeasyPrint's system libraries (text layout and font subsetting).
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    QUOTE_ENGINE_STATIC_DIR=/app/static

WORKDIR /app

# Dependencies first: this layer is reused until the lock file changes.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/src ./src
RUN uv sync --locked --no-dev --no-editable

COPY --from=frontend /frontend/dist ./static

RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"]
CMD ["/app/.venv/bin/uvicorn", "quote_engine.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
