"""Errors as RFC 9457 problem details (``application/problem+json``), never stack traces."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from quote_engine.db.repository import NotFoundError
from quote_engine.engine.errors import InvalidInput, MissingConstant, MissingPrice
from quote_engine.pdf.render import PdfUnavailableError
from quote_engine.services.auth import AuthError, RateLimitedError
from quote_engine.services.documents import PdfBusyError, PdfLimitError
from quote_engine.services.price_csv import CsvError
from quote_engine.services.quotes import QuoteError
from quote_engine.services.sandbox import SandboxError, SandboxFullError, SandboxLimitError
from quote_engine.services.workshops import SetupError

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

    @app.exception_handler(CsvError)
    async def csv_error(_: Request, error: CsvError) -> JSONResponse:
        problems = [
            {"row": p.row, "column": p.column, "message": p.message} for p in error.problems[:200]
        ]
        return problem(422, "the file has problems", str(error), problems=problems)

    @app.exception_handler(SetupError)
    async def setup_error(_: Request, error: SetupError) -> JSONResponse:
        return problem(409, "not allowed now", str(error))

    @app.exception_handler(SandboxError)
    async def sandbox_error(_: Request, error: SandboxError) -> JSONResponse:
        if isinstance(error, SandboxLimitError):
            return problem(429, "too many sandboxes", str(error))
        status = 503 if isinstance(error, SandboxFullError) else 409
        return problem(status, "no sandbox now", str(error))

    @app.exception_handler(PdfLimitError)
    async def pdf_limit(_: Request, error: PdfLimitError) -> JSONResponse:
        return problem(429, "too many PDFs", str(error))

    @app.exception_handler(PdfBusyError)
    async def pdf_busy(_: Request, error: PdfBusyError) -> JSONResponse:
        return problem(503, "PDFs are busy", str(error))

    @app.exception_handler(PdfUnavailableError)
    async def pdf_unavailable(_: Request, error: PdfUnavailableError) -> JSONResponse:
        return problem(503, "PDFs are not available", str(error))
