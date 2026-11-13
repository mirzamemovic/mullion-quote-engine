"""Errors as RFC 9457 problem details (``application/problem+json``), never stack traces."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from quote_engine.db.repository import NotFoundError
from quote_engine.engine.errors import InvalidInput, MissingConstant, MissingPrice
from quote_engine.services.auth import AuthError, RateLimitedError
from quote_engine.services.quotes import QuoteError

PROBLEM = "application/problem+json"


def problem(status: int, title: str, detail: str, **extra: Any) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail, **extra}
    return JSONResponse(body, status_code=status, media_type=PROBLEM)


def install(app: FastAPI) -> None:
    """Register one handler per error family."""

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException) -> JSONResponse:
        return problem(error.status_code, str(error.detail), str(error.detail))

    @app.exception_handler(RequestValidationError)
    async def validation(_: Request, error: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(p) for p in e.get("loc", ())[1:]), "message": e.get("msg", "")}
            for e in error.errors()
        ]
        return problem(422, "invalid input", "some fields are not valid", errors=errors)

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return problem(404, "not found", f"{error.model.__name__} not found")

    @app.exception_handler(MissingConstant)
    async def missing_constant(_: Request, error: MissingConstant) -> JSONResponse:
        return problem(422, "missing catalogue value", str(error), constant=error.name)

    @app.exception_handler(MissingPrice)
    async def missing_price(_: Request, error: MissingPrice) -> JSONResponse:
        return problem(422, "missing price", str(error), item=error.item_ref)

    @app.exception_handler(InvalidInput)
    async def invalid_input(_: Request, error: InvalidInput) -> JSONResponse:
        return problem(422, "invalid input", str(error))

    @app.exception_handler(QuoteError)
    async def quote_error(_: Request, error: QuoteError) -> JSONResponse:
        return problem(409, "not allowed now", str(error))

    @app.exception_handler(RateLimitedError)
    async def rate_limited(_: Request, error: RateLimitedError) -> JSONResponse:
        return problem(429, "too many attempts", str(error))

    @app.exception_handler(AuthError)
    async def auth_error(_: Request, error: AuthError) -> JSONResponse:
        return problem(401, "login failed", str(error))
