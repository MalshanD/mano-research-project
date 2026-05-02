"""
Future-Self Narrative Engine.

Transforms a Seq2Seq projection into a 3-4 sentence first-person
narrative as if the patient were speaking on Day 7 of the projected
plan. Powers the trust-building UX that no academic write-up of these
models has nailed: turning numerical output into language a patient
recognises as themselves.

Design choices
--------------
1. **Groq Llama 3.1 8B when key set, deterministic templates when not.**
   The API key is an *additive* feature — the endpoint always returns
   a usable narrative even at zero external service availability.
2. **Hard regex strip of AI-self-references.** "AI", "model",
   "simulation", "algorithm", "predicted", "calculated" are forbidden.
   On a hit we drop the LLM output and fall back to template.
3. **Single batched call for parallel futures.** Three projections fit
   in one Groq prompt with structured-JSON output, so we burn 1 RPM
   slot rather than 3.
4. **Specific signal references.** When the projection shows a clear
   sleep / stress / quality improvement, the template fallback
   substitutes a literal number ("my sleep has been averaging 7.4
   hours") so the narrative grounds in the user's data, not a generic
   wellness platitude.

UI contract
-----------
``contains_signal_reference`` lets the frontend surface a small "Source
data" disclosure under the narrative card without wasting screen real
estate when the narrative is generic.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

import httpx

from schemas.synthetic.future_self_schema import (
    FutureSelfNarrative,
    FutureSelfRequest,
    ParallelFuturesRequest,
    ParallelFuturesResponse,
    PatientNarrativeContext,
    ScenarioNarrative,
)
from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    RiskLevel,
)

logger = logging.getLogger(__name__)


_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.1-8b-instant"  # free tier
_GROQ_TIMEOUT_SEC = 3.0
_GROQ_TEMPERATURE = 0.7
_GROQ_MAX_TOKENS = 220

# Words the guideline forbids in narratives. Detected as whole words,
# case-insensitive, within word boundaries — so "calculated risk" trips
# but "particularly" does not.
_PROHIBITED = re.compile(
    r"\b(AI|model|models|simulation|algorithm|predicted|calculated|prediction|"
    r"forecasted|generated|inferred)\b",
    flags=re.IGNORECASE,
)


# ── Projection summary helpers ──────────────────────────────────────────────


def _summarise_projection(projection: List[DayVitals]) -> Dict[str, float]:
    """Per-channel mean + last-day for the day-0..day-N projection."""
    n = len(projection)
    if n == 0:
        return {"sleep_avg": 0.0, "sleep_quality_avg": 0.0,
                "heart_rate_avg": 0.0, "stress_avg": 0.0,
                "stress_last": 0.0}
    sleep_avg = sum(d.sleep_hours for d in projection) / n
    sq_avg = sum(d.sleep_quality for d in projection) / n
    hr_avg = sum(d.heart_rate for d in projection) / n
    stress_avg = sum(d.stress_level for d in projection) / n
    return {
        "sleep_avg": float(sleep_avg),
        "sleep_quality_avg": float(sq_avg),
        "heart_rate_avg": float(hr_avg),
        "stress_avg": float(stress_avg),
        "stress_last": float(projection[-1].stress_level),
    }


def _direction(projection: List[DayVitals]) -> str:
    """High-level shape of the trajectory across the projection window.

    Used for template selection.
    """
    if len(projection) < 2:
        return "stable"
    delta = projection[-1].stress_level - projection[0].stress_level
    if delta < -0.05:
        return "improving"
    if delta > 0.05:
        return "worsening"
    return "stable"


# ── Template fallback (no external services required) ──────────────────────


def _template_narrative(
    projection: List[DayVitals], context: PatientNarrativeContext,
) -> str:
    """Deterministic, signal-grounded narrative.

    Structured as 3 sentences:
      1. setting + dominant signal change,
      2. an emotional/lived-experience sentence keyed off direction,
      3. an outlook sentence framing the next chapter.

    All numbers are filled from the actual projection — never invented.
    """
    summary = _summarise_projection(projection)
    direction = _direction(projection)
    concern = (context.primary_concern or "stress").lower()

    sleep = summary["sleep_avg"]
    stress = summary["stress_avg"]
    last_stress = summary["stress_last"]

    if direction == "improving":
        s1 = (
            f"It's day {len(projection)}. I've been averaging {sleep:.1f} "
            f"hours of sleep, and my body feels lighter than it did a week ago."
        )
        if concern in ("sleep", "rest"):
            s2 = (
                "Mornings are easier — I'm not dragging through the first hour "
                "the way I used to."
            )
        elif concern in ("stress", "anxiety"):
            s2 = (
                "The chest-tightness I had on day one has thawed. I still "
                "notice it sometimes, but it doesn't sit on me all day."
            )
        else:
            s2 = (
                "Small things feel manageable again — answering messages, "
                "cooking dinner, looking ahead a little."
            )
        s3 = (
            "If I keep going at this pace, week two should feel like "
            "compounding interest."
        )
    elif direction == "worsening":
        s1 = (
            f"It's day {len(projection)}. My sleep is sitting at {sleep:.1f} "
            f"hours and my body is telling me something needs to change."
        )
        s2 = (
            "Some days feel heavier than others, and that's information — "
            "not failure."
        )
        s3 = (
            "I'd rather notice this now than two weeks from now. I can choose "
            "a different next step."
        )
    else:  # stable
        s1 = (
            f"It's day {len(projection)}. Sleep is averaging {sleep:.1f} "
            f"hours, stress is around {stress:.2f} on the daily scale — "
            f"a steady week."
        )
        s2 = (
            "Nothing dramatic. I think I'm settling into the rhythm rather "
            "than fighting it."
        )
        s3 = (
            "Steady is its own kind of progress. I'll keep an eye on what "
            "starts to shift next."
        )

    return " ".join([s1, s2, s3])


def _signal_referenced(text: str) -> bool:
    """Heuristic: did the narrative cite a specific number?"""
    return bool(re.search(r"\b\d+(\.\d+)?\b", text))


# ── Groq adapter ────────────────────────────────────────────────────────────


def _groq_api_key() -> Optional[str]:
    return os.environ.get("GROQ_API_KEY") or None


def _build_groq_messages(
    summary: Dict[str, float],
    direction: str,
    context: PatientNarrativeContext,
) -> List[Dict[str, str]]:
    intervention = (
        context.intervention_type.name.lower().replace("_", " ")
        if context.intervention_type else "the chosen intervention"
    )
    risk = context.risk_level.value if context.risk_level else "moderate"
    concern = context.primary_concern or "general wellbeing"
    system_prompt = (
        "You are writing a 3-4 sentence first-person reflection from the "
        "patient's perspective on day 7 of their plan. Tone: warm, hopeful, "
        "grounded, never clinical, never diagnostic. NEVER use the words "
        "'AI', 'model', 'simulation', 'algorithm', 'predicted', "
        "'calculated', 'generated', or 'inferred'. Reference a specific "
        "vital improvement (sleep, stress, etc.) using the numbers given. "
        "Output the narrative only — no preamble, no markdown, no quotes."
    )
    user_prompt = (
        f"Trajectory direction: {direction}. "
        f"Average sleep: {summary['sleep_avg']:.1f} hours. "
        f"Average stress: {summary['stress_avg']:.2f}. "
        f"End-of-week stress: {summary['stress_last']:.2f}. "
        f"Primary concern: {concern}. "
        f"Risk level: {risk}. "
        f"Intervention: {intervention}. "
        f"Write the day-7 reflection now."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _call_groq_sync(messages: List[Dict[str, str]]) -> Optional[str]:
    api_key = _groq_api_key()
    if not api_key:
        return None
    try:
        response = httpx.post(
            _GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _GROQ_MODEL,
                "messages": messages,
                "temperature": _GROQ_TEMPERATURE,
                "max_tokens": _GROQ_MAX_TOKENS,
            },
            timeout=_GROQ_TIMEOUT_SEC,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()
        # Strip surrounding quotes the model sometimes adds.
        text = text.strip('"').strip("'")
        return text or None
    except Exception as exc:
        logger.info("groq_unavailable", extra={"error": str(exc)})
        return None


def _scrub(text: str) -> Optional[str]:
    """Reject the LLM output if it contains a prohibited word."""
    if _PROHIBITED.search(text):
        logger.info("groq_output_tripped_prohibited", extra={
            "preview": text[:120],
        })
        return None
    return text


# ── Public API ──────────────────────────────────────────────────────────────


def generate_future_self(req: FutureSelfRequest) -> FutureSelfNarrative:
    summary = _summarise_projection(req.projection)
    direction = _direction(req.projection)

    text: Optional[str] = None
    source = "template"
    if _groq_api_key():
        groq = _call_groq_sync(_build_groq_messages(summary, direction, req.context))
        if groq:
            scrubbed = _scrub(groq)
            if scrubbed:
                text = scrubbed
                source = "groq"

    if text is None:
        text = _template_narrative(req.projection, req.context)
        source = "template"

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    return FutureSelfNarrative(
        narrative=text,
        source=source,
        sentence_count=len(sentences),
        contains_signal_reference=_signal_referenced(text),
    )


def generate_parallel_futures(req: ParallelFuturesRequest) -> ParallelFuturesResponse:
    """Batched parallel-futures call.

    When Groq is available we send ONE request that produces a JSON
    object keyed by scenario name. When Groq is unavailable we fall
    back to the template per scenario — still cheap.
    """
    if len(req.projections) != len(req.scenario_names):
        raise ValueError("projections and scenario_names must be the same length.")

    # Template fallback path (also the default when Groq fails).
    def _template_path() -> ParallelFuturesResponse:
        items = []
        for proj, name in zip(req.projections, req.scenario_names):
            text = _template_narrative(proj, req.context)
            items.append(ScenarioNarrative(scenario_name=name, narrative=text))
        return ParallelFuturesResponse(items=items, source="template")

    if not _groq_api_key():
        return _template_path()

    summaries = [_summarise_projection(p) for p in req.projections]
    directions = [_direction(p) for p in req.projections]
    intervention = (
        req.context.intervention_type.name.lower().replace("_", " ")
        if req.context.intervention_type else "various interventions"
    )

    user_lines = []
    for i, name in enumerate(req.scenario_names):
        s = summaries[i]
        user_lines.append(
            f"- scenario \"{name}\": direction={directions[i]}, "
            f"sleep_avg={s['sleep_avg']:.1f}, stress_avg={s['stress_avg']:.2f}, "
            f"end_stress={s['stress_last']:.2f}"
        )
    system_prompt = (
        "You are writing 3-4 sentence first-person reflections from the "
        "patient's perspective on day 7 of each candidate plan. Tone: "
        "warm, hopeful, grounded, never clinical. NEVER use the words "
        "'AI', 'model', 'simulation', 'algorithm', 'predicted', "
        "'calculated', 'generated', or 'inferred'. Each scenario must "
        "reference at least one specific vital number from the input. "
        "Return strict JSON with one key per scenario, e.g. "
        '{"scenario_name_1": "...", "scenario_name_2": "..."}. '
        "Output JSON only, nothing else."
    )
    user_prompt = (
        f"Compare these scenarios for an intervention strategy "
        f"(\"{intervention}\"):\n" + "\n".join(user_lines) +
        "\nReturn the JSON object now."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = _call_groq_sync(messages)
    if not raw:
        return _template_path()

    # Try to parse the JSON the model returned. Tolerate fenced code
    # blocks and stray prose.
    json_blob = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.+?\})\s*```", json_blob, flags=re.DOTALL)
    if fence:
        json_blob = fence.group(1)
    try:
        parsed = json.loads(json_blob)
    except Exception:
        # Last-ditch: extract braces.
        start = json_blob.find("{")
        end = json_blob.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(json_blob[start:end + 1])
            except Exception:
                return _template_path()
        else:
            return _template_path()

    items: List[ScenarioNarrative] = []
    for name in req.scenario_names:
        text = parsed.get(name) or parsed.get(name.lower()) or ""
        if not text or _PROHIBITED.search(str(text)):
            # If even one scenario fails the scrub, fall back wholesale —
            # parallel narratives need to be apples-to-apples.
            return _template_path()
        items.append(ScenarioNarrative(scenario_name=name, narrative=str(text).strip()))

    return ParallelFuturesResponse(items=items, source="groq")
