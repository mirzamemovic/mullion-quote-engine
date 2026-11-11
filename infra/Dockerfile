# Local-stack image (milestone M0): the backend only.
# M9 replaces this with the multi-stage production build (frontend build, WeasyPrint libraries).
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: this layer is reused until the lock file changes.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/src ./src
RUN uv sync --locked --no-dev --no-editable

RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "quote_engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
