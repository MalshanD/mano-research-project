"""
Researcher-role guard for Component-1 researcher-view endpoints.

Anything mounted under ``/api/v1/researcher/*`` (and the consolidated
researcher-only views below it) sits behind this guard. The guard
recognises two equivalent identity signals:

  1. Bearer JWT in ``Authorization`` whose claim ``role`` (or one of
     ``roles``) contains ``ROLE_RESEARCHER`` (or ``researcher`` —
     case-insensitive). This is the production path.
  2. Header ``X-Role: researcher`` — only honoured when ``settings.env
     != "production"``. This is the development bypass.

Either signal lets the request through. Anything else returns the
structured envelope's 403 ``forbidden`` error. The guard intentionally
returns 403 (not 401) when the JWT is *valid but lacks the role* —
that distinction matters to UX so the SPA can show "ask your admin
for researcher access" instead of "log in".

Why not centralise in middleware. We could attach this in a global
middleware bound to a path prefix, but FastAPI's dependency-injection
is the cleaner expression — each route opts in explicitly via
``Depends(researcher_required)``. That makes researcher-gated routes
greppable.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable, Optional

from fastapi import Depends, Header, Request, status

from core.errors import ErrorCode, MANOAPIError

logger = logging.getLogger(__name__)


# Tokens we recognise as the researcher role. Any case.
_RESEARCHER_TOKENS = frozenset({"researcher", "role_researcher"})


def _role_claims(request: Request) -> Iterable[str]:
    """Pull role-bearing claims out of whatever the auth layer left on
    the request. We support several common shapes so this guard is
    portable across upstream auth changes:

      * ``request.state.user.role`` (str)
      * ``request.state.user.roles`` (list[str])
      * ``request.state.role`` (str)
      * ``request.state.roles`` (list[str])
      * ``request.scope["user"]["role"]`` / "roles"
    """
    candidates = []

    user = getattr(request.state, "user", None)
    for attr in ("role", "roles"):
        if user is not None:
            v = getattr(user, attr, None)
            if v is not None:
                candidates.append(v)
    for attr in ("role", "roles"):
        v = getattr(request.state, attr, None)
        if v is not None:
            candidates.append(v)

    scope_user = request.scope.get("user")
    if isinstance(scope_user, dict):
        for attr in ("role", "roles"):
            v = scope_user.get(attr)
            if v is not None:
                candidates.append(v)

    flat: list[str] = []
    for v in candidates:
        if isinstance(v, str):
            flat.append(v)
        elif isinstance(v, (list, tuple, set)):
            flat.extend(str(x) for x in v)
    return flat


def _is_dev_environment() -> bool:
    """True when the dev-bypass header is allowed."""
    env = (os.environ.get("ENV") or os.environ.get("APP_ENV") or "dev").lower()
    return env not in ("production", "prod")


def researcher_required(
    request: Request,
    x_role: Optional[str] = Header(default=None, alias="X-Role"),
) -> None:
    """Dependency that admits researcher requests and rejects everything else.

    Usage::

        @router.get("/something", dependencies=[Depends(researcher_required)])
        async def something(): ...
    """
    # 1. Dev bypass.
    if _is_dev_environment() and x_role and x_role.strip().lower() in _RESEARCHER_TOKENS:
        return

    # 2. Production path — claim from the request state.
    for claim in _role_claims(request):
        if claim and claim.strip().lower() in _RESEARCHER_TOKENS:
            return

    logger.info(
        "researcher_route_denied",
        extra={"path": request.url.path, "client": request.client.host if request.client else "?"},
    )
    raise MANOAPIError(
        code=ErrorCode.FORBIDDEN,
        message=(
            "This endpoint is restricted to users with the researcher role. "
            "If you believe this is in error, contact your administrator."
        ),
        status_code=status.HTTP_403_FORBIDDEN,
    )
