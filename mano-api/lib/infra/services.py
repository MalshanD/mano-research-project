"""
Dependency registry for long-lived services.

Why a registry, not globals?
----------------------------
Several modules (narrative, weather, pubmed, ambient-sound) keep httpx clients
alive for the lifetime of the process. Without a registry they leak:
  * FastAPI lifespan has no visibility into them → connections stay open.
  * Tests cannot swap them for mocks without monkeypatching every importer.

``services_registry`` gives us one place to:
  * instantiate singletons at app startup (``init_services``),
  * close them cleanly at shutdown (``close_services``),
  * hand them to routes via FastAPI dependency injection.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ServicesRegistry:
    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}

    def register(self, name: str, instance: Any) -> None:
        if name in self._services:
            logger.debug("service_replaced", extra={"name": name})
        self._services[name] = instance

    def get(self, name: str) -> Any:
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")
        return self._services[name]

    def get_optional(self, name: str) -> Optional[Any]:
        return self._services.get(name)

    def all(self) -> Dict[str, Any]:
        return dict(self._services)

    async def close_all(self) -> None:
        for name, svc in list(self._services.items()):
            close = getattr(svc, "close", None) or getattr(svc, "aclose", None)
            if close is None:
                continue
            try:
                result = close()
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:  # pragma: no cover — best effort
                logger.warning("service_close_failed", extra={"name": name, "error": str(exc)})
        self._services.clear()


services_registry = ServicesRegistry()
