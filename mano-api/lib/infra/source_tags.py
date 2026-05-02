"""
Response-source tagging helpers.

Every externally-facing enhancement endpoint returns a ``source`` attribute
indicating how the result was produced:

    live      — fetched from an external API this request
    cached    — served from Redis / in-memory cache
    fallback  — degraded local computation (template narrative, Mixkit library,
                curated PubMed list, etc.)

The frontend uses this tag to annotate cards with trust / freshness signals
and to suppress "this might be stale" banners when we're serving a fallback
that is not, in fact, stale.

Keeping the vocabulary centralised here prevents drift between services.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class SourceTag(str, Enum):
    LIVE = "live"
    CACHED = "cached"
    FALLBACK = "fallback"
    DEGRADED = "degraded"  # partial results, some sub-calls failed


def tag_payload(
    payload: Dict[str, Any],
    source: SourceTag,
    *,
    provider: Optional[str] = None,
    latency_ms: Optional[float] = None,
    cache_key: Optional[str] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Attach a standard ``_meta`` block to an existing payload.

    The underscore prefix is intentional: it keeps meta keys out of the way of
    business attributes when the payload is splatted into a dataframe.
    """
    meta: Dict[str, Any] = {"source": source.value}
    if provider:
        meta["provider"] = provider
    if latency_ms is not None:
        meta["latency_ms"] = round(float(latency_ms), 2)
    if cache_key:
        meta["cache_key"] = cache_key
    if reason:
        meta["reason"] = reason

    # Never clobber a caller-provided _meta — merge instead.
    existing = payload.get("_meta") or {}
    merged = {**existing, **meta}
    return {**payload, "_meta": merged}


def envelope(
    data: Any,
    source: SourceTag,
    *,
    provider: Optional[str] = None,
    latency_ms: Optional[float] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Wrap an arbitrary payload (list, scalar, dict) in a standard envelope.

    Useful for routes whose "data" is a list of studies / sounds / videos
    rather than a single object. The shape is stable across all enhancement
    endpoints so the frontend can parse once.
    """
    meta: Dict[str, Any] = {"source": source.value}
    if provider:
        meta["provider"] = provider
    if latency_ms is not None:
        meta["latency_ms"] = round(float(latency_ms), 2)
    if reason:
        meta["reason"] = reason
    return {"data": data, "_meta": meta}
