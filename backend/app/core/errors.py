"""One JSON shape for every error the API returns:

    {"detail": {"message": "Text the frontend can show as-is", ...extra}}

`extra` is used for things like {"fieldErrors": {"price": "..."}} so a form can
highlight the right fields. src/services/api.js reads exactly this shape.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Raise this from services or routes for an expected problem, e.g.
    raise AppError(404, "Product not found.")"""

    def __init__(self, status_code: int, message: str, **extra):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.extra = extra


def error_response(status_code: int, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": {"message": message, **extra}})


def field_name(location: tuple) -> str:
    # ("body", "customer", "fullName") → "fullName": the name the frontend form uses
    names = [part for part in location if isinstance(part, str) and part not in ("body", "query", "path")]
    return names[-1] if names else "request"


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.message, **exc.extra)


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    # FastAPI's own errors (404 for an unknown URL, 405 wrong method, ...)
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"message": message}},
        headers=getattr(exc, "headers", None),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Request data that doesn't match the Pydantic schema: report every bad field
    field_errors = {}
    for error in exc.errors():
        # Our own validators' messages come as "Value error, <message>"
        message = error["msg"].removeprefix("Value error, ")
        field_errors.setdefault(field_name(error["loc"]), message)
    return error_response(422, "Please fix the highlighted fields.", fieldErrors=field_errors)


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # The full error goes to the server log only; the browser gets a generic message
    # so stack traces, SQL or settings never leak out
    logger.exception("Unhandled error", exc_info=exc)
    return error_response(500, "Something went wrong on our side. Please try again.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
