"""
Unified error envelope for API responses.

Every error — HTTPException, validation failure, unexpected crash — is rendered
in the same shape so the frontend only needs one parser::

    {
      "error": {
        "code": "validation_error",
        "message": "Field 'age' must be between 10 and 120",
        "request_id": "3f2e1a…",
        "details": { ... }     // optional, for dev / non-PII surfaces
      }
    }

The concrete handlers are wired up in ``main.py``. This module provides the
Enum / builder / FastAPI-compatible exception class.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_UNAVAILABLE = "upstream_unavailable"
    MODEL_UNAVAILABLE = "model_unavailable"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    INTERNAL_ERROR = "internal_error"


class MANOAPIError(Exception):
    """Typed exception with the error-envelope shape.

    Prefer raising this over ``HTTPException`` in service code — routes catch
    it centrally and we keep the envelope consistent across every endpoint.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


def build_envelope(
    code: ErrorCode,
    message: str,
    *,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"code": code.value, "message": message}
    if request_id:
        body["request_id"] = request_id
    if details:
        body["details"] = details
    return {"error": body}


# ─── FastAPI exception handlers ────────────────────────────────────────────

async def mano_api_error_handler(request: Request, exc: MANOAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=build_envelope(
            exc.code,
            exc.message,
            request_id=_request_id(request),
            details=exc.details,
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        429: ErrorCode.RATE_LIMITED,
    }.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    detail = exc.detail if isinstance(exc.detail, str) else None
    message = detail or "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=build_envelope(
            code,
            message,
            request_id=_request_id(request),
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Trim validation errors to a compact list — pydantic's raw errors include
    # input echoes which can be large and sometimes contain user PII.
    compact = [
        {
            "loc": ".".join(str(p) for p in err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_envelope(
            ErrorCode.VALIDATION_ERROR,
            "Request validation failed",
            request_id=_request_id(request),
            details={"errors": compact},
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Deliberately do NOT echo ``str(exc)`` — internal error messages may
    # reveal stack frames, DB schema, or secrets.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_envelope(
            ErrorCode.INTERNAL_ERROR,
            "Internal server error",
            request_id=_request_id(request),
        ),
    )


def register_error_handlers(app: Any) -> None:
    """Attach all handlers to a FastAPI app. Call once during app factory."""
    app.add_exception_handler(MANOAPIError, mano_api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
