"""FastAPI application: one process serves the JSON API under ``/api/v1``."""

from fastapi import FastAPI

from quote_engine import __version__
from quote_engine.api import health

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build the application and register its routers."""
    app = FastAPI(
        title="PVC Quote Engine",
        version=__version__,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.include_router(health.router, prefix=API_PREFIX)
    return app


app = create_app()
