"""
Risk Trajectory Tracking — core analysis (pure numpy, no DB, no Keras).

Why this module exists
----------------------
The Keras predictor produces a SNAPSHOT — a single moment in time. Clinicians
need more than that. A patient at score 30 (labelled "Low") trending +6
points / week is more at-risk than a patient stable at 55. This module turns
a time series of historical assessment scores into:

  * a trajectory STATE   — Improving, Stable, Slowly Worsening, Rapidly
                           Worsening, Recovering, Volatile
  * a projection FLAG    — is the score drifting toward a higher risk band
                           even though *every* individual snapshot still
                           reads "Low"?  (This is the headline clinical
                           value-add — without it the system never escalates
                           a slow decline.)
  * derived METRICS      — peak score, rate of change, stability index,
                           days since high-risk event, recovery speed.

Design notes
------------
* Pure numpy — no sqlalchemy, no tensorflow. All storage and Keras wiring
  lives in ``trajectory_service.py``. That separation means this module is
  trivially unit-testable with hand-crafted history arrays.
* Thresholds match ``predictor._get_label``: Low < 35, Moderate 35–70,
  High ≥ 70. Changing those in one place without updating the other would
  produce confusing "Low" labels from the snapshot but "crossing into
  Moderate" alerts from the trajectory — keep them in sync.
* Sparse-data graceful degradation is explicit: a patient with one data
  point gets "Establishing baseline" rather than a garbage slope, and a
  multi-week gap triggers a *partial reset* because drawing a slope across
  "last seen 6 weeks ago" is clinically meaningless.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


# ─── Risk-band thresholds — MUST match predictor._get_label ─────────────────
LOW_THRESHOLD = 35.0       # score < 35 ⇒ Low
MODERATE_THRESHOLD = 70.0  # 35 ≤ score < 70 ⇒ Moderate; ≥ 70 ⇒ High

LABEL_LOW = "Low"
LABEL_MODERATE = "Moderate"
LABEL_HIGH = "High"


# ─── Trajectory states (strings so they serialise straight to JSON) ─────────
STATE_IMPROVING = "Improving"
STATE_STABLE = "Stable"
STATE_SLOWLY_WORSENING = "Slowly Worsening"
STATE_RAPIDLY_WORSENING = "Rapidly Worsening"
STATE_RECOVERING = "Recovering"
STATE_VOLATILE = "Volatile"
STATE_ESTABLISHING_BASELINE = "Establishing baseline"   # 1-session fallback

TRAJECTORY_STATES = (
    STATE_IMPROVING,
    STATE_STABLE,
    STATE_SLOWLY_WORSENING,
    STATE_RAPIDLY_WORSENING,
    STATE_RECOVERING,
    STATE_VOLATILE,
    STATE_ESTABLISHING_BASELINE,
)


# ─── Tunable thresholds (documented so clinicians can audit) ────────────────
# How many recent sessions feed the slope. Matches the spec's worked example.
DEFAULT_WINDOW_SIZE = 4

# Sessions with fewer than this many points fall back to low-confidence rules.
MIN_SESSIONS_FOR_TREND = 3

# A rolling window of scores that stay within ±STABLE_BAND_POINTS is "Stable".
STABLE_BAND_POINTS = 5.0

# Slope ≥ this many points/week → Rapidly Worsening.
RAPID_WORSENING_SLOPE = 8.0

# Standard deviation across the window ≥ this → Volatile.
VOLATILITY_STD_POINTS = 12.0

# Gap (days between consecutive sessions) above which we refuse to draw a
# trendline. Matches the spec's "no check-in for 6 weeks" example.
DEFAULT_GAP_RESET_DAYS = 42

# Horizon (in days) we extrapolate the slope over when deciding whether a
# "Low" score will cross 35 soon. 2 weeks matches the spec's example.
WORSENING_PROJECTION_DAYS = 14

# High-risk event threshold for the "days since last high" counter.
HIGH_RISK_EVENT_THRESHOLD = MODERATE_THRESHOLD  # score ≥ 70 counts as "high"


# ─── Dataclasses ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SessionPoint:
    """One assessment's worth of data for one condition (stress/anxiety/depression)."""
    timestamp: datetime
    score: float

    def to_dict(self) -> Dict:
        return {"timestamp": self.timestamp.isoformat(), "score": float(self.score)}


@dataclass(frozen=True)
class DerivedMetrics:
    """Numbers clinicians and the UI can surface directly."""
    peak_score: float                  # worst ever reached
    peak_timestamp: Optional[str]      # ISO-formatted, None if no history
    days_since_last_high: Optional[int]  # None if no high event ever recorded
    rate_of_change_per_week: float     # points per week, positive = worsening
    stability_index: float             # std-dev across window (high = volatile)
    recovery_speed_per_week: Optional[float]  # None if no recovery underway
    change_since_last: Optional[float]  # (current - previous), None if 1 point

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass(frozen=True)
class TrajectoryResult:
    """Full trajectory analysis for ONE condition."""
    head: str                          # "stress" | "anxiety" | "depression"
    current_score: Optional[float]     # most recent score, None if no history
    current_level: Optional[str]       # Low/Moderate/High of current_score
    state: str                         # TRAJECTORY_STATES value
    confidence: str                    # "high" | "low" | "baseline"
    sessions_worsening: int            # # of consecutive worsening sessions
    sessions_used: int                 # # of points actually used for the slope
    worsening_in_low_flag: bool        # the headline projection flag
    alert: Optional[str]               # human-readable flag text
    metrics: DerivedMetrics
    summary: str                       # short human-readable paragraph

    def to_dict(self) -> Dict:
        return {
            "head": self.head,
            "current_score": self.current_score,
            "current_level": self.current_level,
            "state": self.state,
            "confidence": self.confidence,
            "sessions_worsening": self.sessions_worsening,
            "sessions_used": self.sessions_used,
            "worsening_in_low_flag": self.worsening_in_low_flag,
            "alert": self.alert,
            "metrics": self.metrics.to_dict(),
            "summary": self.summary,
        }


# ─── Helpers ────────────────────────────────────────────────────────────────

def level_for_score(score: float) -> str:
    """Map a raw score to its risk-band label. Mirrors predictor._get_label."""
    if score < LOW_THRESHOLD:
        return LABEL_LOW
    if score < MODERATE_THRESHOLD:
        return LABEL_MODERATE
    return LABEL_HIGH


def _sort_points(points: Sequence[SessionPoint]) -> List[SessionPoint]:
    """Return points ordered oldest → newest. Safe on arbitrary input order."""
    return sorted(points, key=lambda p: p.timestamp)


def _trim_after_gap(points: List[SessionPoint], gap_days: int) -> List[SessionPoint]:
    """Drop history older than the most recent gap of ``gap_days`` or more.

    The spec is explicit: "don't draw a trend line across a large time gap."
    If a patient stopped checking in for 6+ weeks, the new session is a
    partial reset — only history *after* the gap feeds the slope.
    """
    if len(points) < 2:
        return list(points)

    cutoff_idx = 0
    for i in range(1, len(points)):
        delta = (points[i].timestamp - points[i - 1].timestamp).days
        if delta >= gap_days:
            cutoff_idx = i  # anything before this is stale
    return list(points[cutoff_idx:])


def _weeks_between(earlier: datetime, later: datetime) -> float:
    """Fractional weeks between two timestamps. Always non-negative."""
    seconds = (later - earlier).total_seconds()
    return max(0.0, seconds / (7 * 86400))


def compute_slope(points: Sequence[SessionPoint]) -> float:
    """Least-squares slope of score-vs-time in **points per week**.

    We use time-in-weeks as the x-axis (rather than session index) because
    sessions aren't evenly spaced. A user who checks in twice in a day then
    not again for three weeks shouldn't look like they're worsening fast
    just because their score happens to be higher today.
    """
    if len(points) < 2:
        return 0.0

    anchor = points[0].timestamp
    xs = np.array([_weeks_between(anchor, p.timestamp) for p in points], dtype=float)
    ys = np.array([p.score for p in points], dtype=float)

    # If every session is on the same calendar week the x-values collapse to 0
    # and polyfit would raise. Fall back to "no slope signal".
    if xs.max() - xs.min() < 1e-9:
        return 0.0

    slope, _intercept = np.polyfit(xs, ys, deg=1)
    return float(slope)


def classify_trajectory(
    points: Sequence[SessionPoint],
    slope_per_week: float,
) -> str:
    """Pick one of the six states (plus the baseline fallback) for this window.

    Priority order matters — Volatile is checked first because high standard
    deviation can coexist with a small slope, and we want the volatility
    signal to win in that case. Recovering beats Improving when the peak
    was genuinely bad (≥ Moderate) and we're coming down off it.
    """
    if len(points) == 0:
        return STATE_ESTABLISHING_BASELINE
    if len(points) == 1:
        return STATE_ESTABLISHING_BASELINE

    scores = np.array([p.score for p in points], dtype=float)

    # Priority ladder — check rapid, directional decline/climb BEFORE
    # Volatile, because a monotonic rise from 20→55 has high std-dev but
    # the clinical reading is "getting worse fast", not "chaotic". Volatile
    # is reserved for swings that don't tell a consistent directional story.
    if slope_per_week >= RAPID_WORSENING_SLOPE:
        return STATE_RAPIDLY_WORSENING

    # Recovering — came off a Moderate-or-worse peak and the slope is down.
    peak = scores.max()
    latest = scores[-1]
    if slope_per_week < 0 and peak >= MODERATE_THRESHOLD and latest < peak:
        return STATE_RECOVERING

    # Volatile — wide swings that aren't a clean up/down story.
    if scores.std() >= VOLATILITY_STD_POINTS:
        return STATE_VOLATILE

    # Stable — span across the window stays inside ±STABLE_BAND_POINTS.
    if scores.max() - scores.min() <= STABLE_BAND_POINTS:
        return STATE_STABLE

    # Direction + magnitude.
    if slope_per_week <= -1.0:
        return STATE_IMPROVING
    if slope_per_week >= 1.0:
        return STATE_SLOWLY_WORSENING

    # Small absolute slope and not flat enough for Stable — call it Stable
    # as the conservative default. Avoids flagging noise as "Worsening".
    return STATE_STABLE


def project_crosses_threshold(
    current_score: float,
    slope_per_week: float,
    threshold: float,
    horizon_days: int,
) -> bool:
    """True if extrapolating the slope would push score past ``threshold``
    within ``horizon_days``. Only makes sense when slope is positive and
    current_score is below threshold."""
    if slope_per_week <= 0:
        return False
    if current_score >= threshold:
        return False
    weeks = horizon_days / 7.0
    projected = current_score + slope_per_week * weeks
    return projected >= threshold


def derive_metrics(
    all_points: Sequence[SessionPoint],
    window_points: Sequence[SessionPoint],
    slope_per_week: float,
) -> DerivedMetrics:
    """Pull out the headline numbers: peak, rate of change, stability, etc.

    ``all_points`` is the user's entire history (for peak + days-since-high).
    ``window_points`` is the trimmed recent window (for stability index).
    """
    if not all_points:
        return DerivedMetrics(
            peak_score=0.0, peak_timestamp=None, days_since_last_high=None,
            rate_of_change_per_week=0.0, stability_index=0.0,
            recovery_speed_per_week=None, change_since_last=None,
        )

    scores_all = np.array([p.score for p in all_points], dtype=float)
    peak_idx = int(np.argmax(scores_all))
    peak_score = float(scores_all[peak_idx])
    peak_timestamp = all_points[peak_idx].timestamp.isoformat()

    # Days since last score that counted as "high-risk".
    latest_ts = all_points[-1].timestamp
    days_since_high: Optional[int] = None
    for p in reversed(all_points):
        if p.score >= HIGH_RISK_EVENT_THRESHOLD:
            days_since_high = max(0, (latest_ts - p.timestamp).days)
            break

    # Stability index — std-dev over the recent window. Low = flat, high = swingy.
    window_scores = np.array([p.score for p in window_points], dtype=float)
    stability_index = float(window_scores.std()) if len(window_scores) >= 2 else 0.0

    # Recovery speed — only meaningful when (a) the peak is recent-ish and
    # (b) the current slope is negative. Reports the magnitude of that fall.
    recovery_speed: Optional[float] = None
    if slope_per_week < 0 and peak_score >= MODERATE_THRESHOLD:
        if peak_idx < len(all_points) - 1:  # peak is in the past, not the latest point
            recovery_speed = float(-slope_per_week)

    # Change since last session.
    change_since_last: Optional[float] = None
    if len(all_points) >= 2:
        change_since_last = float(all_points[-1].score - all_points[-2].score)

    return DerivedMetrics(
        peak_score=round(peak_score, 2),
        peak_timestamp=peak_timestamp,
        days_since_last_high=days_since_high,
        rate_of_change_per_week=round(slope_per_week, 2),
        stability_index=round(stability_index, 2),
        recovery_speed_per_week=round(recovery_speed, 2) if recovery_speed is not None else None,
        change_since_last=round(change_since_last, 2) if change_since_last is not None else None,
    )


def _consecutive_worsening(points: Sequence[SessionPoint]) -> int:
    """# of most-recent sessions whose score rose vs the previous session.

    Walks backwards from the newest point and stops at the first non-rising
    delta. The spec surfaces this as "sessions_worsening" so the UI can say
    "3 consecutive sessions getting worse".
    """
    if len(points) < 2:
        return 0
    count = 0
    for i in range(len(points) - 1, 0, -1):
        if points[i].score > points[i - 1].score:
            count += 1
        else:
            break
    return count


def _build_alert(
    head: str,
    state: str,
    current_score: float,
    current_level: str,
    slope_per_week: float,
    worsening_in_low: bool,
    sessions_worsening: int,
    points_span_days: int,
) -> Optional[str]:
    """Compose the most clinically useful single-sentence alert.

    We return ``None`` when nothing alert-worthy is happening, so the UI can
    skip the row entirely rather than rendering an empty warning strip.
    """
    head_cap = head.capitalize()

    if worsening_in_low:
        return (
            f"{head_cap} score has risen at ~{slope_per_week:.1f} pts/week over "
            f"{points_span_days} days; on track to cross into {LABEL_MODERATE} "
            f"within ~{WORSENING_PROJECTION_DAYS} days despite the current {LABEL_LOW} label."
        )

    if state == STATE_RAPIDLY_WORSENING:
        return (
            f"{head_cap} is deteriorating rapidly — slope ~{slope_per_week:.1f} pts/week "
            f"over {sessions_worsening} consecutive worsening sessions. Current {current_level}."
        )

    if state == STATE_SLOWLY_WORSENING and sessions_worsening >= 3:
        return (
            f"{head_cap} shows a sustained upward drift — {sessions_worsening} consecutive "
            f"sessions worsening at ~{slope_per_week:.1f} pts/week."
        )

    if state == STATE_VOLATILE:
        return (
            f"{head_cap} readings are volatile; large swings between sessions. "
            f"High volatility is itself a risk signal even when the average score is moderate."
        )

    return None


def _build_summary(
    head: str,
    state: str,
    confidence: str,
    current_score: Optional[float],
    current_level: Optional[str],
    slope_per_week: float,
    sessions_used: int,
) -> str:
    """Single-paragraph human summary. Intentionally short — the UI will
    pair it with a sparkline and the alert row."""
    head_cap = head.capitalize()

    if confidence == "baseline":
        return (
            f"{head_cap}: establishing baseline from the first assessment. "
            f"At least {MIN_SESSIONS_FOR_TREND} sessions are needed before a "
            f"reliable trend can be drawn."
        )

    level_phrase = f" (currently {current_level})" if current_level else ""
    direction = (
        "rising" if slope_per_week > 0 else "falling" if slope_per_week < 0 else "flat"
    )

    if confidence == "low":
        return (
            f"{head_cap}: preliminary {state.lower()} trend{level_phrase}. "
            f"Only {sessions_used} sessions available — direction is {direction} "
            f"at ~{slope_per_week:+.1f} pts/week but treat with low confidence."
        )

    return (
        f"{head_cap}: {state.lower()}{level_phrase}. "
        f"{sessions_used}-session window, slope {slope_per_week:+.1f} pts/week."
    )


# ─── Public API ─────────────────────────────────────────────────────────────

def analyse_condition(
    head: str,
    points: Sequence[SessionPoint],
    window_size: int = DEFAULT_WINDOW_SIZE,
    gap_reset_days: int = DEFAULT_GAP_RESET_DAYS,
) -> TrajectoryResult:
    """Full trajectory analysis for ONE condition's history.

    ``points`` may arrive in any order — we sort defensively. All sparse-
    data and gap-reset rules are applied here so the caller doesn't need to
    know about them.
    """
    ordered = _sort_points(points)

    # No history at all — return an explicit empty result rather than erroring.
    if not ordered:
        empty_metrics = DerivedMetrics(
            peak_score=0.0, peak_timestamp=None, days_since_last_high=None,
            rate_of_change_per_week=0.0, stability_index=0.0,
            recovery_speed_per_week=None, change_since_last=None,
        )
        return TrajectoryResult(
            head=head, current_score=None, current_level=None,
            state=STATE_ESTABLISHING_BASELINE, confidence="baseline",
            sessions_worsening=0, sessions_used=0,
            worsening_in_low_flag=False, alert=None, metrics=empty_metrics,
            summary=_build_summary(head, STATE_ESTABLISHING_BASELINE, "baseline",
                                    None, None, 0.0, 0),
        )

    # Partial-reset rule: drop anything older than the most recent long gap.
    post_gap = _trim_after_gap(ordered, gap_reset_days)

    # Slope window — the N most-recent post-gap points.
    window = post_gap[-window_size:] if len(post_gap) > window_size else list(post_gap)

    current_score = float(ordered[-1].score)
    current_level = level_for_score(current_score)

    # Sparse-data branches — mirror the spec:
    #   1 session   → baseline, no slope
    #   2 sessions  → direction only, low confidence
    #   3+ sessions → full analysis
    n = len(window)
    if n == 1:
        confidence = "baseline"
        slope = 0.0
        state = STATE_ESTABLISHING_BASELINE
    elif n < MIN_SESSIONS_FOR_TREND:
        confidence = "low"
        slope = compute_slope(window)
        state = classify_trajectory(window, slope)
    else:
        confidence = "high"
        slope = compute_slope(window)
        state = classify_trajectory(window, slope)

    metrics = derive_metrics(ordered, window, slope)
    sessions_worsening = _consecutive_worsening(window)

    worsening_in_low = (
        confidence != "baseline"
        and current_level == LABEL_LOW
        and project_crosses_threshold(
            current_score=current_score,
            slope_per_week=slope,
            threshold=LOW_THRESHOLD,
            horizon_days=WORSENING_PROJECTION_DAYS,
        )
    )

    points_span_days = (
        (window[-1].timestamp - window[0].timestamp).days if n >= 2 else 0
    )
    alert = _build_alert(
        head=head, state=state, current_score=current_score,
        current_level=current_level, slope_per_week=slope,
        worsening_in_low=worsening_in_low, sessions_worsening=sessions_worsening,
        points_span_days=points_span_days,
    )

    summary = _build_summary(
        head=head, state=state, confidence=confidence,
        current_score=current_score, current_level=current_level,
        slope_per_week=slope, sessions_used=n,
    )

    return TrajectoryResult(
        head=head,
        current_score=round(current_score, 2),
        current_level=current_level,
        state=state,
        confidence=confidence,
        sessions_worsening=sessions_worsening,
        sessions_used=n,
        worsening_in_low_flag=worsening_in_low,
        alert=alert,
        metrics=metrics,
        summary=summary,
    )


def analyse_all_conditions(
    history: Dict[str, Sequence[SessionPoint]],
    window_size: int = DEFAULT_WINDOW_SIZE,
    gap_reset_days: int = DEFAULT_GAP_RESET_DAYS,
) -> Dict[str, TrajectoryResult]:
    """Run ``analyse_condition`` for each head present in ``history``."""
    return {
        head: analyse_condition(head, pts, window_size=window_size,
                                 gap_reset_days=gap_reset_days)
        for head, pts in history.items()
    }
