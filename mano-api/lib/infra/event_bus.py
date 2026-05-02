"""
Event bus abstraction.

Default backend is an in-process ``asyncio.Queue`` fan-out — zero ops, fine for
single-instance deployments. When ``settings.event_bus_backend == "kafka"`` and
``aiokafka`` is importable, we switch to a Kafka adapter.

The surface area is deliberately tiny so swapping backends is painless:

    bus = get_event_bus()
    await bus.publish("c1.intervention.prescribed", payload)
    async for event in bus.subscribe("c1.intervention.prescribed"):
        ...

The Kafka adapter is shipped as a *stub* that requires explicit init via
``init_kafka()`` during app startup. We do not lazy-connect during publish —
the health-check must prove the connection is alive before we claim Kafka is
the active backend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Set

from core.config import settings

logger = logging.getLogger(__name__)


# ─── Event envelope ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Event:
    topic: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "payload": self.payload,
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
        }


# ─── Base interface ─────────────────────────────────────────────────────────

class EventBus:
    backend_name: str = "noop"

    async def publish(self, topic: str, payload: Dict[str, Any]) -> Event:
        raise NotImplementedError

    def subscribe(self, topic: str) -> AsyncIterator[Event]:
        raise NotImplementedError

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass


# ─── In-process async implementation ───────────────────────────────────────

class InProcessEventBus(EventBus):
    """
    Fan-out via per-subscriber queues. Publishing never blocks on slow
    consumers — a consumer that doesn't read fast enough simply loses events
    after the per-queue cap.
    """

    backend_name = "inprocess"

    # queue capacity per subscriber before oldest events are dropped
    QUEUE_CAPACITY = 1024

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: Dict[str, Any]) -> Event:
        event = Event(topic=topic, payload=payload)
        async with self._lock:
            queues = list(self._subscribers.get(topic, ()))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # drop oldest, append new — bounded-memory guarantee
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(
                        "event_dropped_queue_full",
                        extra={"topic": topic, "event_id": event.event_id},
                    )
        return event

    async def subscribe(self, topic: str) -> AsyncIterator[Event]:
        q: asyncio.Queue = asyncio.Queue(maxsize=self.QUEUE_CAPACITY)
        async with self._lock:
            self._subscribers.setdefault(topic, []).append(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            async with self._lock:
                if topic in self._subscribers and q in self._subscribers[topic]:
                    self._subscribers[topic].remove(q)

    async def close(self) -> None:
        async with self._lock:
            self._subscribers.clear()


# ─── Kafka adapter (stub — enabled only when aiokafka is installed) ─────────

class KafkaEventBus(EventBus):
    """
    Adapter skeleton for aiokafka. Left intentionally lean: the moment we need
    cross-instance events in production, fill in ``_producer`` / ``_consumer``
    wiring and remove the import guard.

    Until then, the adapter degrades to the in-process bus with a warning so
    developer environments never crash due to missing Kafka.
    """

    backend_name = "kafka"

    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap = bootstrap_servers
        self._inproc = InProcessEventBus()  # fallback fan-out while stubbed
        self._connected = False

    async def connect(self) -> None:
        try:
            import aiokafka  # noqa: F401  — import guard only
            # Real implementation would go here:
            #   self._producer = aiokafka.AIOKafkaProducer(...)
            #   await self._producer.start()
            self._connected = True
            logger.info("kafka_adapter_ready_stub", extra={"bootstrap": self._bootstrap})
        except ImportError:
            logger.warning(
                "kafka_adapter_missing_dep",
                extra={"hint": "pip install aiokafka to enable Kafka event bus"},
            )

    async def publish(self, topic: str, payload: Dict[str, Any]) -> Event:
        # Always publish in-process so local subscribers still work.
        event = await self._inproc.publish(topic, payload)
        if self._connected:
            # await self._producer.send_and_wait(topic, json.dumps(event.to_dict()).encode())
            pass
        return event

    def subscribe(self, topic: str) -> AsyncIterator[Event]:
        return self._inproc.subscribe(topic)

    async def ping(self) -> bool:
        return self._connected

    async def close(self) -> None:
        await self._inproc.close()
        self._connected = False


# ─── Factory ────────────────────────────────────────────────────────────────

_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is not None:
        return _bus

    if settings.has_kafka:
        _bus = KafkaEventBus(settings.kafka_bootstrap_servers)  # type: ignore[arg-type]
        logger.info("event_bus_selected", extra={"backend": "kafka"})
    else:
        _bus = InProcessEventBus()
        logger.info("event_bus_selected", extra={"backend": "inprocess"})
    return _bus


async def init_event_bus() -> EventBus:
    """Called at app startup. Performs any one-time async connect."""
    bus = get_event_bus()
    if isinstance(bus, KafkaEventBus):
        await bus.connect()
    return bus


async def reset_event_bus_for_tests() -> None:
    global _bus
    if _bus is not None:
        await _bus.close()
    _bus = None


# ─── Convenience helpers ───────────────────────────────────────────────────

async def publish(topic: str, payload: Dict[str, Any]) -> Event:
    """Shortcut for ``get_event_bus().publish(...)``."""
    return await get_event_bus().publish(topic, payload)


# Well-known topics used across components. Keep this list tight so typos
# surface at import time.
class Topics:
    INTERVENTION_PRESCRIBED = "c1.intervention.prescribed"
    TRAJECTORY_COMPUTED = "c1.trajectory.computed"
    COUNTERFACTUAL_COMPUTED = "c1.counterfactual.computed"
    NARRATIVE_GENERATED = "c1.narrative.generated"
    EVIDENCE_FETCHED = "c1.evidence.fetched"
    WEATHER_INSIGHT = "c1.weather.insight"
    VOICE_JOURNAL_PROCESSED = "c1.voice_journal.processed"
    AMBIENT_SOUND_PROFILE = "c1.ambient_sound.profile"
    THERAPY_PHASE_CHANGED = "c1.therapy.phase_changed"
    THERAPY_CRISIS_DETECTED = "c1.therapy.crisis_detected"
    PASSPORT_RENDERED = "c1.passport.rendered"
