"""Health endpoint, polled by the deploy script, the container health check and the uptime monitor.

It answers 200 when the process is up and the database answers, and 503 when the database does
not, so a deploy never switches to a container that cannot reach its data.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from quote_engine import __version__
from quote_engine.db.session import get_engine

router = APIRouter(tags=["health"])


class Health(BaseModel):
    """What the service reports about itself."""

    status: Literal["ok", "degraded"]
    version: str
    database: Literal["ok", "down"]


def database_answers() -> bool:
    """One ``SELECT 1``; any database error counts as down (the error itself is not shown)."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


@router.get("/health", responses={503: {"model": Health, "description": "Database down"}})
def read_health(
    response: Response, database_ok: Annotated[bool, Depends(database_answers)]
) -> Health:
    """Report that the process is up, which version is running, and whether the database answers."""
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return Health(status="degraded", version=__version__, database="down")
    return Health(status="ok", version=__version__, database="ok")
