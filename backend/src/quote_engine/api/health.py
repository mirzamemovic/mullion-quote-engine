"""Health endpoint, polled by the deploy script and the uptime monitor."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from quote_engine import __version__

router = APIRouter(tags=["health"])


class Health(BaseModel):
    """What the service reports about itself."""

    status: Literal["ok"]
    version: str


@router.get("/health")
def read_health() -> Health:
    """Report that the process is up, and which version is running."""
    return Health(status="ok", version=__version__)
