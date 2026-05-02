"""
Per-IP rate limiting via slowapi (FastAPI wrapper around limits).

Limits are tiered by cost class:

    default — cheap CRUD endpoints            (e.g. 100/minute)
    ml      — inference routes (Seq2Seq, etc) (e.g.  20/minute)
    llm     — third-party LLM calls           (e.g.  10/minute)

Routes decorate themselves declaratively::

    from lib.infra.rate_limit import limiter, LIMIT_ML

    @router.post("/predict_risk")
    @limiter.limit(LIMIT_ML)
    async def predict_risk(request: Request, ...):

The slowapi middleware is registered in ``main.py``. If slowapi isn't
installed, a no-op limiter is substituted so the app still boots.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from core.config import settings

logger = logging.getLogger(__name__)


class _NoopLimiter:
    """Stand-in when slowapi is unavailable — every decorator is identity."""

    def limit(self, *_args: Any, **_kwargs: Any) -> Callable[[Callable], Callable]:
        def _wrapper(fn: Callable) -> Callable:
            return fn
        return _wrapper

    def exempt(self, fn: Callable) -> Callable:  # pragma: no cover
        return fn


try:
    from slowapi import Limiter  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.rate_limit_default],
        headers_enabled=True,
    )
    _RATE_LIMITER_READY = True
except ImportError:  # pragma: no cover
    limiter = _NoopLimiter()  # type: ignore[assignment]
    _RATE_LIMITER_READY = False
    logger.warning(
        "slowapi_missing",
        extra={"hint": "pip install slowapi to enable rate limiting"},
    )


# Limit strings exposed as module-level constants so routes use a single
# source of truth. Do not inline these strings at call sites.
LIMIT_DEFAULT = settings.rate_limit_default
LIMIT_ML = settings.rate_limit_ml
LIMIT_LLM = settings.rate_limit_llm


def register_rate_limiter(app: Any) -> None:
    """Wire limiter state + exception handler into a FastAPI application."""
    if not _RATE_LIMITER_READY:
        return

    try:
        from slowapi.errors import RateLimitExceeded  # type: ignore
        from slowapi.middleware import SlowAPIMiddleware  # type: ignore
        from slowapi import _rate_limit_exceeded_handler  # type: ignore
    except ImportError:  # pragma: no cover
        return

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    logger.info(
        "rate_limiter_registered",
        extra={
            "default": LIMIT_DEFAULT,
            "ml": LIMIT_ML,
            "llm": LIMIT_LLM,
        },
    )
