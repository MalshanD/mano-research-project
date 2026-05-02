"""
Infrastructure primitives shared across all MANO components.

Modules here are intentionally framework-agnostic (no FastAPI imports) so they
can be unit-tested in isolation and re-used by CLI jobs, scheduled tasks, and
batch researchers alike.

Public surface:
    cache         — CacheBackend (Redis with in-memory fallback)
    event_bus     — EventBus abstraction (in-process asyncio / Kafka adapter)
    scheduler     — APScheduler wrapper for periodic jobs
    security      — input sanitisation, log scrubbing
    rate_limit    — slowapi integration
    source_tags   — response-source tagging helpers
    services      — singleton service registry
"""
