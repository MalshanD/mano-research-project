"""
Thin wrapper around APScheduler for periodic background jobs.

Use cases in Component 1:
  * Nightly refresh of the PubMed curated-evidence cache (cuts cold-start
    latency for /evidence to near-zero).
  * Hourly prune of expired entries from the in-memory cache fallback.
  * Daily roll-up of cohort simulation aggregates for the researcher module.

APScheduler is an optional dependency. If not installed, the module exports a
no-op scheduler so the rest of the code can call ``schedule_*`` functions
without guards.

Scheduling surface is tiny on purpose. Anything more complex (cron-style
triggers, multi-node coordination) should graduate to a dedicated worker.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
    from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
    from apscheduler.triggers.cron import CronTrigger  # type: ignore
    _APS_AVAILABLE = True
except ImportError:  # pragma: no cover
    AsyncIOScheduler = None  # type: ignore[assignment]
    IntervalTrigger = None  # type: ignore[assignment]
    CronTrigger = None  # type: ignore[assignment]
    _APS_AVAILABLE = False


class _NoopScheduler:
    running = False

    def add_interval_job(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def add_cron_job(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def start(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


class MANOScheduler:
    """Async scheduler with a narrow schedule_* API."""

    def __init__(self) -> None:
        if _APS_AVAILABLE:
            self._scheduler = AsyncIOScheduler()
        else:
            self._scheduler = _NoopScheduler()
            logger.warning(
                "scheduler_dep_missing",
                extra={"hint": "pip install apscheduler to enable periodic jobs"},
            )

    @property
    def running(self) -> bool:
        return bool(getattr(self._scheduler, "running", False))

    def schedule_interval(
        self,
        job_id: str,
        fn: Callable[..., Any],
        *,
        seconds: int,
        run_on_start: bool = False,
    ) -> None:
        if not _APS_AVAILABLE:
            return
        self._scheduler.add_job(
            fn,
            trigger=IntervalTrigger(seconds=seconds),
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        if run_on_start:
            # Fire once immediately — APScheduler does not expose a cleaner
            # "run on startup" affordance for intervals.
            self._scheduler.add_job(fn, id=f"{job_id}:boot", replace_existing=True)
        logger.info("scheduler_interval_job", extra={"job_id": job_id, "seconds": seconds})

    def schedule_cron(
        self,
        job_id: str,
        fn: Callable[..., Any],
        *,
        hour: str = "*",
        minute: str = "0",
    ) -> None:
        if not _APS_AVAILABLE:
            return
        self._scheduler.add_job(
            fn,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("scheduler_cron_job", extra={"job_id": job_id, "hour": hour, "minute": minute})

    def start(self) -> None:
        if self._scheduler and not self.running:
            self._scheduler.start()
            logger.info("scheduler_started")

    def shutdown(self) -> None:
        if self._scheduler and self.running:
            self._scheduler.shutdown(wait=False)
            logger.info("scheduler_stopped")


_scheduler: Optional[MANOScheduler] = None


def get_scheduler() -> MANOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = MANOScheduler()
    return _scheduler
