"""FastAPI application: one process serves the JSON API under ``/api/v1`` and the built frontend.

The frontend is served from the folder in ``QUOTE_ENGINE_STATIC_DIR`` (``/app/static`` in the
image) when that folder exists; in development the Vite dev server serves it instead.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from quote_engine import __version__
from quote_engine.api import health

API_PREFIX = "/api/v1"
STATIC_DIR_ENV = "QUOTE_ENGINE_STATIC_DIR"
DEFAULT_STATIC_DIR = Path("/app/static")


def static_dir() -> Path | None:
    """The built frontend's folder, or ``None`` when there is none to serve."""
    folder = Path(os.environ.get(STATIC_DIR_ENV, str(DEFAULT_STATIC_DIR)))
    return folder if (folder / "index.html").is_file() else None


def create_app() -> FastAPI:
    """Build the application: the API routers first, then the frontend at ``/``."""
    app = FastAPI(
        title="PVC Quote Engine",
        version=__version__,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.include_router(health.router, prefix=API_PREFIX)
    frontend = static_dir()
    if frontend is not None:
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
