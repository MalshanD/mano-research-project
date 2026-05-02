"""
MANO Middleware Stack.
Handles cross-cutting concerns: request logging, error handling, request IDs.

WHAT IS MIDDLEWARE?
Middleware sits between the client and your route handlers. Every request passes
through it on the way IN, and every response passes through on the way OUT.
Think of it as a security checkpoint at the airport — all traffic must go through it.

                  Request                  Response
    Client ─────► [Middleware] ─────► Route ─────► [Middleware] ─────► Client
"""
import time
import uuid
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import get_logger

logger = get_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with timing information.

    For each request, it logs:
    - A unique request_id (for tracing in distributed systems)
    - HTTP method and path
    - Response status code
    - Processing duration in milliseconds
    """

    async def dispatch(self, request: Request, call_next):
        # Generate a unique ID for this request (useful for debugging)
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Record start time
        start_time = time.perf_counter()

        # Log the incoming request
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
        )

        # Pass to the next handler (could be another middleware or the route)
        response = await call_next(request)

        # Calculate processing time
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Log the outgoing response
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # Attach request_id to response headers (so the frontend can reference it)
        response.headers["X-Request-ID"] = request_id
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler. Catches ANY unhandled exception and returns
    a consistent JSON error response instead of a raw HTML traceback.

    WHY?
    Without this, if your model inference crashes with a shape mismatch,
    the client gets a raw 500 error page. With this, they get:
    {
        "error": "Internal Server Error",
        "detail": "descriptive message",
        "request_id": "abc123"
    }
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            # Get request_id if it was set by RequestLoggingMiddleware
            request_id = getattr(request.state, "request_id", "unknown")

            # Log the full traceback for debugging
            logger.error(
                "unhandled_exception",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error_type=type(exc).__name__,
                error_message=str(exc),
                traceback=traceback.format_exc(),
            )

            # Return a clean JSON response to the client
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": f"{type(exc).__name__}: {str(exc)}",
                    "request_id": request_id,
                },
            )
