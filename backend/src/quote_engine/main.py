"""FastAPI application: one process serves the JSON API under ``/api/v1`` and the built frontend.

The frontend is served from the folder in ``QUOTE_ENGINE_STATIC_DIR`` (``/app/static`` in the
image) when that folder exists; in development the Vite dev server serves it instead.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from quote_engine import __version__
from quote_engine.api import (
    health,
    problems,
    routes_admin,
    routes_auth,
    routes_clients,
    routes_quotes,
)
from quote_engine.settings import get_settings

API_PREFIX = "/api/v1"
STATIC_DIR_ENV = "QUOTE_ENGINE_STATIC_DIR"
DEFAULT_STATIC_DIR = Path("/app/static")


class SinglePageApp(StaticFiles):
    """Static files, plus ``index.html`` for app routes such as ``/quotes/12`` on a reload.

    Paths under ``api/`` and paths that name a file (with an extension) still get their 404.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            route = path.replace("\\", "/")  # StaticFiles uses the OS separator
            is_app_route = "." not in route.rsplit("/", 1)[-1] and not route.startswith("api/")
            if error.status_code != 404 or not is_app_route:
                raise
            return await super().get_response("index.html", scope)


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
    problems.install(app)
    for router in (
        health.router,
        routes_auth.router,
        routes_clients.router,
        routes_quotes.router,
        routes_admin.router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    if get_settings().dev_demo:
        # Development only, never in production: see settings.py and api/routes_dev.py.
        from quote_engine.api import routes_dev

        app.include_router(routes_dev.router, prefix=API_PREFIX)
    frontend = static_dir()
    if frontend is not None:
        app.mount("/", SinglePageApp(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
