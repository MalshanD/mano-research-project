"""
Test suite for ``lib.therapy.safety_guard``.

Verifies the guideline's hard invariants for the therapy flagship's
hardcoded crisis safety net:

  1. Total keyword count is at least 30, spread across 4 tiers.
  2. Every keyword in every tier triggers a crisis result.
  3. Highest-tier match wins when multiple tiers fire on the same input.
  4. Empty / whitespace / None input is safe (no crisis, no exception).
  5. Borderline benign text does not produce false positives.
  6. P95 scan latency over 200 random-length inputs is below 10 ms.
  7. Hotlines accompany every crisis response and are non-empty.
  8. Crisis responses never contain any of the words the guideline
     prohibits ("AI", "model", "simulation", "algorithm", "predicted",
     "calculated").
  9. The module imports without pulling in torch / sqlalchemy / httpx
     — the safety net must remain reachable when the rest of the system
     is degraded.
"""

from __future__ import annotations

import importlib
import re
import statistics
import sys
import time
from typing import List

import pytest

from lib.therapy.safety_guard import (
    CrisisSeverity,
    SafetyScanResult,
    hotlines,
    keyword_count,
    keywords_for,
    scan,
)


# ─── 1. Keyword count ────────────────────────────────────────────────────────


def test_keyword_count_meets_guideline_minimum() -> None:
    assert keyword_count() >= 30, (
        f"Guideline requires 30+ crisis keywords across 4 tiers; "
        f"current count is {keyword_count()}"
    )


def test_all_four_tiers_have_keywords() -> None:
    for severity in CrisisSeverity:
        terms = keywords_for(severity)
        assert len(terms) >= 5, (
            f"Tier {severity.value} has only {len(terms)} keywords; "
            f"each tier should have at least 5 distinct terms."
        )


# ─── 2. Every keyword triggers ───────────────────────────────────────────────


@pytest.mark.parametrize("severity", list(CrisisSeverity))
def test_every_keyword_in_tier_triggers_crisis(severity: CrisisSeverity) -> None:
    """Each individual keyword, embedded in a sentence, must trigger.

    We embed the keyword in a realistic-looking sentence so that the
    regex's word-boundary handling is exercised against punctuation and
    whitespace, not just the bare term.
    """
    for keyword in keywords_for(severity):
        message = f"i feel like i'm going to {keyword} tonight."
        result = scan(message)
        assert result.is_crisis, f"Keyword {keyword!r} (tier={severity.value}) failed to trigger"
        # The matched tier must be at least this severity (a higher tier
        # may fire if the embedding sentence happens to also match a
        # CRITICAL term, which is fine).
        assert result.severity is not None
        assert result.severity.rank >= severity.rank, (
            f"Keyword {keyword!r} matched at tier {result.severity.value}, "
            f"expected at least {severity.value}"
        )


# ─── 3. Highest tier wins ────────────────────────────────────────────────────


def test_highest_tier_wins_when_multiple_tiers_match() -> None:
    # "hopeless" is MEDIUM, "want to die" is CRITICAL — CRITICAL should win.
    message = "i feel hopeless and i want to die"
    result = scan(message)
    assert result.is_crisis
    assert result.severity == CrisisSeverity.CRITICAL


def test_high_wins_over_medium_low() -> None:
    # "overwhelmed" is LOW, "hurt myself" is HIGH.
    message = "i'm overwhelmed and want to hurt myself"
    result = scan(message)
    assert result.is_crisis
    assert result.severity == CrisisSeverity.HIGH


# ─── 4. Empty / whitespace / None safety ─────────────────────────────────────


@pytest.mark.parametrize("payload", [None, "", "   ", "\n\t\n"])
def test_empty_inputs_are_not_crisis(payload) -> None:
    result = scan(payload)
    assert isinstance(result, SafetyScanResult)
    assert result.is_crisis is False
    assert result.severity is None
    assert result.matched_keywords == []
    assert result.crisis_response is None
    assert result.hotlines == []


# ─── 5. No false positives on benign / borderline text ───────────────────────


_BENIGN_MESSAGES: List[str] = [
    "I had a great day at work today.",
    "The presentation went really well and I'm proud of myself.",
    "Tomorrow I'll try the new gym class my friend recommended.",
    "I love rainy mornings — they make the coffee taste better.",
    "I'm going to die laughing if she tells that joke again.",  # idiom, must NOT trip
    "She killed it on stage last night.",                        # idiom
    "That movie was so emotional, I cried for an hour.",
    "The deadline is killer but I'll get through it.",
    "I'm tired but happy.",
    "Self-care is important — I'm starting therapy on Monday.",  # 'self ' adjacent to 'harm' would be tricky but we say 'self-care'
]


@pytest.mark.parametrize("message", _BENIGN_MESSAGES)
def test_benign_messages_do_not_false_positive(message: str) -> None:
    result = scan(message)
    assert result.is_crisis is False, (
        f"Benign message tripped the safety guard at "
        f"{result.severity.value if result.severity else '?'}: {message!r} "
        f"(matches: {result.matched_keywords})"
    )


# ─── 6. Latency budget (P95 < 10 ms) ─────────────────────────────────────────


def test_scan_p95_latency_under_10ms() -> None:
    """Run 200 representative scans and assert P95 < 10 ms.

    The corpus mixes empty input, short benign, long benign, short
    crisis, and a 5 000-char paragraph that is mostly noise with one
    crisis term embedded. The P95 latency must remain under the
    guideline's 10 ms budget regardless of payload size.
    """
    long_haystack = ("the weather has been pleasant lately and i went for a walk. "
                     * 100) + " i want to die at the end of this paragraph."
    corpus = [
        "",
        "hello",
        "i had a calm day, nothing eventful, slept ok",
        "i feel hopeless",
        "i want to die",
        "self-harm is on my mind",
        "i can't go on like this",
        long_haystack,
        "the weather is great today",
        "i'm overwhelmed but coping",
    ] * 20

    timings_ms: List[float] = []
    for message in corpus:
        t0 = time.perf_counter()
        scan(message)
        timings_ms.append((time.perf_counter() - t0) * 1000.0)

    timings_ms.sort()
    p95 = timings_ms[int(len(timings_ms) * 0.95)]
    p50 = statistics.median(timings_ms)
    assert p95 < 10.0, (
        f"Safety guard P95 latency exceeded 10 ms budget: "
        f"P50={p50:.3f} ms, P95={p95:.3f} ms over {len(timings_ms)} scans"
    )


# ─── 7. Hotlines + crisis response wiring ────────────────────────────────────


def test_crisis_response_includes_hotlines_and_copy() -> None:
    result = scan("i want to die")
    assert result.is_crisis
    assert result.severity == CrisisSeverity.CRITICAL
    assert result.crisis_response, "Crisis result must include user-facing copy"
    assert len(result.hotlines) >= 3, "At least three hotlines must accompany every crisis response"
    for line in result.hotlines:
        assert "name" in line and "number" in line and "url" in line, (
            f"Hotline entry missing required fields: {line}"
        )


def test_hotlines_are_immutable_to_callers() -> None:
    """Mutating the returned hotlines must not mutate the module's source."""
    snapshot = list(hotlines())
    if snapshot:
        snapshot[0]["name"] = "TAMPERED"
    refetched = list(hotlines())
    assert refetched[0]["name"] != "TAMPERED"


# ─── 8. Crisis response wording — no AI/model/simulation/etc. leakage ────────


_PROHIBITED_WORDS = re.compile(
    r"\b(AI|model|simulation|algorithm|predicted|calculated)\b",
    flags=re.IGNORECASE,
)


@pytest.mark.parametrize(
    "message,expected_severity",
    [
        ("i want to die",            CrisisSeverity.CRITICAL),
        ("i want to hurt myself",    CrisisSeverity.HIGH),
        ("i feel hopeless",          CrisisSeverity.MEDIUM),
        ("i'm overwhelmed",          CrisisSeverity.LOW),
    ],
)
def test_crisis_responses_never_use_prohibited_words(message: str, expected_severity: CrisisSeverity) -> None:
    result = scan(message)
    assert result.is_crisis
    assert result.severity == expected_severity
    assert result.crisis_response is not None
    assert not _PROHIBITED_WORDS.search(result.crisis_response), (
        f"Crisis response for {expected_severity.value} contains prohibited word "
        f"({result.crisis_response!r})"
    )


# ─── 9. Module isolation — no heavy imports ──────────────────────────────────


def test_safety_guard_does_not_import_heavy_dependencies() -> None:
    """Reload the module in isolation and assert it does not pull in
    torch, transformers, sqlalchemy, httpx, redis, or kafka. The safety
    net must remain reachable when those services are degraded or
    absent.
    """
    # Take a baseline snapshot of loaded modules.
    forbidden = {"torch", "transformers", "sqlalchemy", "httpx", "redis", "aiokafka"}

    # Drop our module + any cached children so reload sees the import
    # graph fresh.
    for name in list(sys.modules):
        if name == "lib.therapy.safety_guard" or name.startswith("lib.therapy.safety_guard."):
            del sys.modules[name]

    # Mark which forbidden modules were already loaded by other tests
    # so we don't blame the safety guard for someone else's imports.
    pre_loaded = {m for m in forbidden if m in sys.modules}

    importlib.import_module("lib.therapy.safety_guard")

    introduced = {m for m in forbidden if m in sys.modules} - pre_loaded
    assert not introduced, (
        f"Importing lib.therapy.safety_guard pulled in forbidden modules: "
        f"{sorted(introduced)}. The safety net must remain reachable when "
        f"these services are degraded."
    )
