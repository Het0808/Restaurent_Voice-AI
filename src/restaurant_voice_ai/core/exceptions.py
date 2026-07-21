"""Application exceptions and safe HTTP exception handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from restaurant_voice_ai.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base exception for expected application failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "APPLICATION_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(ApplicationError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(
            message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class BusinessValidationError(ApplicationError):
    """Raised when a request violates an application rule."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


def error_content(code: str, message: str) -> dict[str, Any]:
    return ErrorResponse(code=code, message=message).model_dump()


async def application_error_handler(_: Request, exc: ApplicationError) -> JSONResponse:
    """Convert expected application errors to stable public responses."""
    logger.warning("Application error", extra={"error_code": exc.code})
    return JSONResponse(status_code=exc.status_code, content=error_content(exc.code, exc.message))


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures and return a detail-free response."""
    logger.exception("Unhandled application exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_content("INTERNAL_SERVER_ERROR", "An unexpected error occurred"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers."""
    app.add_exception_handler(ApplicationError, application_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
