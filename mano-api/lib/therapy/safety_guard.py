"""
Therapy Safety Guard — hardcoded crisis keyword detection.

This module is the **first** line of defense in the Guided Therapy Session
flagship feature. Per the Component-1 revamp guideline:

    "Runs on EVERY message regardless of phase --- cannot be disabled.
     Crisis keyword regex (30+ terms across 4 severity tiers --- hardcoded,
     not LLM-dependent). If crisis detected: freeze session immediately,
     return crisis response with hotline numbers, emit CRITICAL Kafka event
     to C2 & C3, set session to CRISIS_HOLD."

Design invariants
-----------------
1. **Pure function with no I/O.** ``scan(text)`` performs only in-process
   regex matching against precompiled patterns. No DB, no HTTP, no LLM.
2. **Hard latency budget: <10 ms** per scan, regardless of how many other
   services are slow or down. Verified by ``tests/test_safety_guard.py``.
3. **No external dependencies.** Importing this module must not import
   torch, transformers, sqlalchemy, or any service that requires
   environment variables to be set. This guarantees the safety net is
   reachable even when the rest of the system is degraded.
4. **Non-LLM, non-ML.** Pattern matching only. No fuzzy embeddings, no
   model inference. The guideline is explicit: hardcoded.
5. **Tiered severity, not boolean.** Four tiers (CRITICAL, HIGH, MEDIUM,
   LOW) with the same response shape. Highest matched tier wins.
6. **False-positive tolerance > false-negative tolerance.** A spurious
   CRITICAL flag merely surfaces hotlines and pauses the session — costly
   but recoverable. A missed CRITICAL is a safety failure. Tune patterns
   accordingly.

The hotline list at the bottom is authoritative for this deployment.
Update it via PR; do not configure it from environment variables (this
keeps the safety net reachable even if env loading is broken).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Severity model
# ─────────────────────────────────────────────────────────────────────────────


class CrisisSeverity(str, Enum):
    """Four-tier severity, ordered by descending urgency."""

    CRITICAL = "critical"   # Imminent self-harm / suicide intent
    HIGH = "high"           # Active self-harm ideation, severe distress
    MEDIUM = "medium"       # Hopelessness, marked despair
    LOW = "low"             # Generalised acute distress

    @property
    def rank(self) -> int:
        return {
            CrisisSeverity.CRITICAL: 4,
            CrisisSeverity.HIGH: 3,
            CrisisSeverity.MEDIUM: 2,
            CrisisSeverity.LOW: 1,
        }[self]


# ─────────────────────────────────────────────────────────────────────────────
# Hardcoded keyword tiers
#
# Curated against:
#   - SAMHSA National Suicide Prevention Lifeline lexicons
#   - Vanderbilt CSSRS keyword set (public excerpts)
#   - Existing lib/activity/crisis_service.py keywords (for parity)
#
# Notes on form:
#   - Phrases (multi-word) are preferred over single words to reduce false
#     positives. "die" alone hits "I'd die for that pizza"; "want to die"
#     does not.
#   - All entries are lowercase. The scanner lowercases input once.
#   - We use word-boundary regex so "suicidology" doesn't trip "suicid".
# ─────────────────────────────────────────────────────────────────────────────

_CRITICAL_TERMS: Tuple[str, ...] = (
    "kill myself",
    "killing myself",
    "suicide",
    "suicidal",
    "end my life",
    "ending my life",
    "want to die",
    "going to end it",
    "going to kill myself",
    "take my own life",
    "end it all",
    "better off dead",
    "plan to die",
    "ready to die",
    "tonight i will",     # common pattern in suicide notes
    "writing my note",
)

_HIGH_TERMS: Tuple[str, ...] = (
    "self-harm",
    "self harm",
    "selfharm",
    "hurt myself",
    "hurting myself",
    "cutting myself",
    "cut myself",
    "overdose",
    "no reason to live",
    "can't go on",
    "cannot go on",
    "don't want to be alive",
    "do not want to be alive",
    "rather be dead",
    "wish i was dead",
    "wish i were dead",
    "nothing left",
    "can't take it anymore",
    "cannot take it anymore",
    "not worth living",
    "goodbye forever",
)

_MEDIUM_TERMS: Tuple[str, ...] = (
    "hopeless",
    "give up",
    "giving up",
    "worthless",
    "nobody cares",
    "no one cares",
    "can't cope",
    "cannot cope",
    "falling apart",
    "broken inside",
    "what's the point",
    "what is the point",
    "done trying",
    "tired of living",
    "no one would miss me",
    "trapped",
    "drowning",
    "empty inside",
)

_LOW_TERMS: Tuple[str, ...] = (
    "really struggling",
    "dark place",
    "everything is wrong",
    "can't handle",
    "cannot handle",
    "overwhelmed",
    "losing control",
    "don't know what to do",
    "do not know what to do",
    "rock bottom",
    "burnt out",
    "burned out",
    "exhausted with everything",
)


_TIERS: Tuple[Tuple[CrisisSeverity, Tuple[str, ...]], ...] = (
    (CrisisSeverity.CRITICAL, _CRITICAL_TERMS),
    (CrisisSeverity.HIGH, _HIGH_TERMS),
    (CrisisSeverity.MEDIUM, _MEDIUM_TERMS),
    (CrisisSeverity.LOW, _LOW_TERMS),
)


def _compile(tiers: Tuple[Tuple[CrisisSeverity, Tuple[str, ...]], ...]) -> Dict[CrisisSeverity, re.Pattern]:
    """Build one combined regex per tier. Word-boundary anchored.

    Compilation happens at import time (module load), so each ``scan()``
    call is cheap — only the matchers run.
    """
    compiled: Dict[CrisisSeverity, re.Pattern] = {}
    for severity, terms in tiers:
        # Sort longer phrases first so "kill myself" wins over "kill" if we
        # ever add a single-word "kill" entry. Currently all are phrases,
        # but this keeps the invariant explicit.
        ordered = sorted(terms, key=len, reverse=True)
        # ``re.escape`` so "self-harm" doesn't break the pattern.
        alternation = "|".join(re.escape(t) for t in ordered)
        # Use lookarounds for "soft" word boundaries that respect spaces
        # and punctuation but treat hyphens (e.g. "self-harm") and
        # apostrophes (e.g. "can't") as part of the term.
        pattern = re.compile(r"(?:^|[^a-zA-Z0-9])(" + alternation + r")(?:$|[^a-zA-Z0-9])")
        compiled[severity] = pattern
    return compiled


_COMPILED: Dict[CrisisSeverity, re.Pattern] = _compile(_TIERS)


# Total keyword count surfaced for sanity-checking against the guideline
# ("30+ terms"). Computed at import.
_KEYWORD_COUNT: int = sum(len(terms) for _, terms in _TIERS)


# ─────────────────────────────────────────────────────────────────────────────
# Hotlines (authoritative for this deployment)
# ─────────────────────────────────────────────────────────────────────────────

# Order: international + local-to-deployment-region. The first hotline
# returned is the one shown most prominently in the UI; subsequent ones
# are listed below it.
_HOTLINES: Tuple[Dict[str, str], ...] = (
    {
        "name": "988 Suicide & Crisis Lifeline (US/Canada)",
        "number": "988",
        "channel": "call_or_text",
        "url": "https://988lifeline.org/",
        "hours": "24/7",
    },
    {
        "name": "Sumithrayo (Sri Lanka)",
        "number": "+94 11 2696666",
        "channel": "call",
        "url": "https://srilankasumithrayo.lk/",
        "hours": "Daily 09:00–20:00",
    },
    {
        "name": "NIMH 1926 (Sri Lanka National Mental Health Helpline)",
        "number": "1926",
        "channel": "call",
        "url": "https://nimh.health.gov.lk/",
        "hours": "24/7",
    },
    {
        "name": "Samaritans (UK & ROI)",
        "number": "116 123",
        "channel": "call",
        "url": "https://www.samaritans.org/",
        "hours": "24/7",
    },
    {
        "name": "Befrienders Worldwide",
        "number": "(directory)",
        "channel": "directory",
        "url": "https://befrienders.org/find-support-now/",
        "hours": "directory of 349 centres in 32 countries",
    },
)


# ─────────────────────────────────────────────────────────────────────────────
# Public scan API
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SafetyScanResult:
    """Result of one ``scan()`` call.

    Attributes
    ----------
    is_crisis: bool
        ``True`` iff at least one keyword matched.
    severity: CrisisSeverity | None
        The highest tier matched. ``None`` when ``is_crisis`` is False.
    matched_keywords: list[str]
        Distinct keywords that triggered (lowercased).
    matched_per_tier: dict[CrisisSeverity, list[str]]
        Diagnostic breakdown for logging / metrics.
    crisis_response: str | None
        Verbatim response copy to show the user when ``is_crisis``. Always
        non-None when ``is_crisis`` is True. Frontend should render this
        ABOVE any LLM-generated content (which the orchestrator is also
        required to suppress on crisis).
    hotlines: list[dict]
        Hotline directory to render with the response. Empty when not in
        crisis.
    scan_latency_ms: float
        Wall-clock latency of this scan, for observability + the test
        suite's <10 ms assertion.
    """

    is_crisis: bool
    severity: Optional[CrisisSeverity] = None
    matched_keywords: List[str] = field(default_factory=list)
    matched_per_tier: Dict[CrisisSeverity, List[str]] = field(default_factory=dict)
    crisis_response: Optional[str] = None
    hotlines: List[Dict[str, str]] = field(default_factory=list)
    scan_latency_ms: float = 0.0


def _crisis_response_for(severity: CrisisSeverity) -> str:
    """Verbatim response copy by tier.

    These strings are rendered in the chat UI. They are deliberately
    short, calm, non-clinical, and avoid the language the guideline
    prohibits ("AI", "model", "simulation", "algorithm", "predicted",
    "calculated"). They never reach an LLM — the orchestrator returns
    them directly.
    """
    if severity == CrisisSeverity.CRITICAL:
        return (
            "I hear that you’re in a lot of pain right now, and I’m really "
            "glad you said something. What you’re feeling matters, and you "
            "don’t have to face it alone. Please reach out to one of the "
            "lines below right now — a person on the other end is ready to "
            "talk with you, day or night. If you’re in immediate danger, "
            "please call your local emergency number."
        )
    if severity == CrisisSeverity.HIGH:
        return (
            "Thank you for trusting me with that. What you’re describing is "
            "serious, and you deserve support that’s closer than I can be. "
            "Please consider reaching out to one of the lines below — they "
            "are trained to listen without judgement and they’re available "
            "now. You don’t have to figure this out alone."
        )
    if severity == CrisisSeverity.MEDIUM:
        return (
            "It sounds like things feel really heavy right now. That kind "
            "of pain is real, and it can lift — especially when you don’t "
            "carry it alone. If you’d like to talk to someone live, the "
            "lines below are there for exactly this. We can also slow this "
            "session down whenever you need to."
        )
    # LOW
    return (
        "I’m glad you’re here. What you’re feeling sounds genuinely hard. "
        "If at any point you’d like to talk to a person live, the lines "
        "below are open. Otherwise, we can keep going at whatever pace "
        "feels right for you."
    )


def scan(text: Optional[str]) -> SafetyScanResult:
    """Scan free-form user text for crisis indicators.

    This is the function that **every** therapy message endpoint must call
    first, before any LLM, classifier, or downstream service. It returns
    in well under 10 ms even on long messages because:
      * patterns are pre-compiled,
      * we only run four ``re.findall`` calls per scan,
      * we operate on a single lowercased copy of the input,
      * we cap input length at 10 000 chars (longer texts are truncated;
        LLM-side sanitisation will reject anyway).

    The function is idempotent and side-effect-free; the caller is
    responsible for transitioning the session to CRISIS_HOLD and
    publishing the corresponding event on the bus when ``is_crisis``.
    """
    started = time.perf_counter()

    if not text:
        return SafetyScanResult(
            is_crisis=False,
            scan_latency_ms=(time.perf_counter() - started) * 1000.0,
        )

    # Defensive truncation. Real LLM sanitiser also caps at 2000, but the
    # guard runs first and we want a guaranteed bound regardless.
    if len(text) > 10_000:
        text = text[:10_000]

    haystack = text.lower()

    matched_per_tier: Dict[CrisisSeverity, List[str]] = {}
    for severity, pattern in _COMPILED.items():
        # findall returns the captured group (the matched term) for each match.
        hits = pattern.findall(haystack)
        if hits:
            # Deduplicate while preserving first-seen order — useful for
            # logs / diagnostics.
            seen = set()
            unique_hits: List[str] = []
            for h in hits:
                if h not in seen:
                    seen.add(h)
                    unique_hits.append(h)
            matched_per_tier[severity] = unique_hits

    if not matched_per_tier:
        return SafetyScanResult(
            is_crisis=False,
            scan_latency_ms=(time.perf_counter() - started) * 1000.0,
        )

    # Highest tier wins — sort by severity rank descending.
    top_severity = max(matched_per_tier.keys(), key=lambda s: s.rank)
    flat_matches: List[str] = []
    for severity in (CrisisSeverity.CRITICAL, CrisisSeverity.HIGH, CrisisSeverity.MEDIUM, CrisisSeverity.LOW):
        flat_matches.extend(matched_per_tier.get(severity, []))

    return SafetyScanResult(
        is_crisis=True,
        severity=top_severity,
        matched_keywords=flat_matches,
        matched_per_tier=matched_per_tier,
        crisis_response=_crisis_response_for(top_severity),
        hotlines=[dict(h) for h in _HOTLINES],
        scan_latency_ms=(time.perf_counter() - started) * 1000.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public introspection helpers (for tests + diagnostics)
# ─────────────────────────────────────────────────────────────────────────────


def keyword_count() -> int:
    """Return the total number of distinct crisis keywords across all tiers."""
    return _KEYWORD_COUNT


def keywords_for(severity: CrisisSeverity) -> Tuple[str, ...]:
    """Return the tuple of keywords for a given severity tier."""
    for sev, terms in _TIERS:
        if sev == severity:
            return terms
    return ()


def hotlines() -> Tuple[Dict[str, str], ...]:
    """Return the immutable hotline directory."""
    return tuple(dict(h) for h in _HOTLINES)
