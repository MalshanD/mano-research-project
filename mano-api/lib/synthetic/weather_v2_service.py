"""
Consolidated Weather-Mood / SAD service.

Replaces the older ``weather_service`` + ``weather_mood_service`` pair
(flagged as duplicate in the C1 audit) with a single coherent surface:

  * geolocation resolution — caller-supplied lat/lon → ip-api.com →
    Colombo fallback (so the endpoint never returns 5xx),
  * weather fetch — Open-Meteo (no key, no rate limit),
  * SAD risk formula — evidence-based linear combination clamped to [0, 1],
  * 12 recommendation templates with UI render hints
    (severity_color, icon_hint, recommendation_id),
  * a flat schema the UI binds directly to without further reshaping.

Performance: a typical call is ~1 HTTP request to Open-Meteo
(~250 ms) + 1 optional ip-api request when no lat/lon is supplied.
We cache the 6-hour Open-Meteo response in process memory keyed on
(lat, lon) rounded to 0.05 degrees.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from schemas.synthetic.weather_v2_schema import (
    MoodModifier,
    WeatherDayForecast,
    WeatherForecastResponse,
    WeatherMoodContext,
    WeatherSnapshot,
)

logger = logging.getLogger(__name__)


_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_IP_API_URL = "http://ip-api.com/json/"
_FALLBACK_LAT = 6.9271      # Colombo, Sri Lanka
_FALLBACK_LON = 79.8612
_FALLBACK_LABEL = "Colombo, Sri Lanka"
_HTTP_TIMEOUT_SEC = 2.5
_CACHE_TTL_SEC = 6 * 3600

_HOURLY_VARS = (
    "uv_index,sunshine_duration,cloudcover,precipitation,temperature_2m,"
    "apparent_temperature,windspeed_10m"
)
_DAILY_VARS = (
    "uv_index_max,sunshine_duration,precipitation_sum,temperature_2m_max,"
    "temperature_2m_min,windspeed_10m_max"
)


# ── In-process cache ──────────────────────────────────────────────────────


_cache: Dict[Tuple[float, float], Tuple[float, dict]] = {}


def _cache_get(key: Tuple[float, float]) -> Optional[dict]:
    item = _cache.get(key)
    if not item:
        return None
    written_at, payload = item
    if time.time() - written_at > _CACHE_TTL_SEC:
        _cache.pop(key, None)
        return None
    return payload


def _cache_set(key: Tuple[float, float], payload: dict) -> None:
    _cache[key] = (time.time(), payload)


# ── Geolocation ───────────────────────────────────────────────────────────


def _resolve_location(
    lat: Optional[float], lon: Optional[float],
) -> Tuple[float, float, str, str]:
    """Returns (lat, lon, label, source).

    Caller-supplied → ip-api.com → Colombo fallback.
    """
    if lat is not None and lon is not None:
        return float(lat), float(lon), f"Custom ({lat:.3f}, {lon:.3f})", "caller_supplied"

    try:
        r = httpx.get(_IP_API_URL, timeout=_HTTP_TIMEOUT_SEC)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            city = data.get("city") or "Unknown city"
            country = data.get("country") or ""
            label = f"{city}{', ' + country if country else ''} (auto-detected via IP)"
            return float(data["lat"]), float(data["lon"]), label, "ip_api"
    except Exception as exc:
        logger.info("ip_api_unavailable", extra={"error": str(exc)})

    return _FALLBACK_LAT, _FALLBACK_LON, _FALLBACK_LABEL, "fallback_colombo"


# ── Open-Meteo fetch ──────────────────────────────────────────────────────


def _fetch_weather(lat: float, lon: float) -> Optional[dict]:
    """Returns the Open-Meteo response dict or None if unreachable."""
    key = (round(lat, 2), round(lon, 2))
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        r = httpx.get(
            _OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": _HOURLY_VARS,
                "daily": _DAILY_VARS,
                "current": "temperature_2m,apparent_temperature,cloudcover,uv_index",
                "timezone": "auto",
                "forecast_days": 7,
            },
            timeout=_HTTP_TIMEOUT_SEC,
        )
        r.raise_for_status()
        data = r.json()
        _cache_set(key, data)
        return data
    except Exception as exc:
        logger.info("open_meteo_unavailable", extra={"error": str(exc)})
        return None


# ── SAD risk formula ──────────────────────────────────────────────────────


def _sad_risk(snap: WeatherSnapshot) -> float:
    """Evidence-based linear formula, clamped to [0, 1].

    UV index < 2:                 +0.25
    Cloud cover > 80%:            +0.20
    Sunshine duration < 2 h:      +0.20
    Precipitation > 5 mm:         +0.10
    Apparent temperature < 15°C:  +0.10

    Each input is treated as 0 contribution when None.
    """
    score = 0.0
    if snap.uv_index is not None and snap.uv_index < 2.0:
        score += 0.25
    if snap.cloud_cover_pct is not None and snap.cloud_cover_pct > 80.0:
        score += 0.20
    if snap.sunshine_hours is not None and snap.sunshine_hours < 2.0:
        score += 0.20
    if snap.precipitation_mm is not None and snap.precipitation_mm > 5.0:
        score += 0.10
    if snap.apparent_temperature_c is not None and snap.apparent_temperature_c < 15.0:
        score += 0.10
    return float(max(0.0, min(1.0, score)))


def _severity(score: float) -> Tuple[str, str, str]:
    """Map SAD score → (label, color, icon)."""
    if score >= 0.65:
        return "high", "rose-600", "cloud-rain"
    if score >= 0.40:
        return "elevated", "orange-500", "cloud-fog"
    if score >= 0.20:
        return "moderate", "amber-500", "cloud"
    return "low", "emerald-500", "sun"


# ── 12 recommendation templates ───────────────────────────────────────────
#
# Keyed by (severity_label, dominant_signal). dominant_signal picked
# by which contributor of the SAD score has the largest weight on the
# day in question. Recommendations all use everyday language; none
# mention "AI" / "model" etc.


_RECOMMENDATIONS: Dict[str, Tuple[str, str]] = {
    # severity:dominant_signal → (recommendation_id, copy)
    "high:precipitation": (
        "rec.high.precip",
        "Heavy rain plus low light is hard on mood. Try a 10-minute indoor "
        "stretch and a warm drink before lunch — small grounding wins help.",
    ),
    "high:low_uv": (
        "rec.high.low_uv",
        "Today's weather may be affecting your mood. A few minutes near a "
        "bright window, or a short outdoor walk before noon, can lift it.",
    ),
    "high:cold": (
        "rec.high.cold",
        "It's chilly enough that going outside feels harder. Wrap up warm and "
        "do a quick five-minute walk anyway — your future self will thank you.",
    ),
    "elevated:precipitation": (
        "rec.elev.precip",
        "Rainy days make staying active harder. An indoor yoga session or a "
        "short body-scan meditation can help maintain your energy.",
    ),
    "elevated:cloud_cover": (
        "rec.elev.cloud",
        "Heavily overcast skies. Try opening curtains fully and stepping "
        "outside even briefly — natural light, however muted, still helps.",
    ),
    "elevated:short_sunshine": (
        "rec.elev.sunshine",
        "Limited sunshine today. A 10-minute walk during the brightest hour "
        "can give your body the light cue it's looking for.",
    ),
    "elevated:cold": (
        "rec.elev.cold",
        "Cooler than your body likes. A warm drink, a shower, and an early "
        "wind-down routine tonight will help.",
    ),
    "moderate:low_uv": (
        "rec.mod.low_uv",
        "Light UV exposure today. If you can fit a short walk in before noon, "
        "your circadian rhythm will appreciate it.",
    ),
    "moderate:cloud_cover": (
        "rec.mod.cloud",
        "Cloudier than usual. Open the windows wide and let in what light there is.",
    ),
    "moderate:short_sunshine": (
        "rec.mod.sunshine",
        "Sunshine is on the short side. Bundle a brief outdoor break into your "
        "lunch hour if you can.",
    ),
    "low:high_uv": (
        "rec.low.high_uv",
        "Great conditions for a mood-boosting walk. Morning sunlight before "
        "10 a.m. is most effective for setting your day up well.",
    ),
    "low:default": (
        "rec.low.default",
        "Pleasant weather. Spending a little time outside today is an easy win.",
    ),
}


def _dominant_signal(snap: WeatherSnapshot) -> str:
    """Pick the largest single contributor for recommendation routing."""
    candidates = []
    if snap.precipitation_mm is not None and snap.precipitation_mm > 5.0:
        candidates.append(("precipitation", 0.10 + snap.precipitation_mm / 100.0))
    if snap.uv_index is not None and snap.uv_index < 2.0:
        candidates.append(("low_uv", 0.25))
    if snap.uv_index is not None and snap.uv_index >= 5.0:
        candidates.append(("high_uv", snap.uv_index / 10.0))
    if snap.cloud_cover_pct is not None and snap.cloud_cover_pct > 80.0:
        candidates.append(("cloud_cover", snap.cloud_cover_pct / 100.0))
    if snap.sunshine_hours is not None and snap.sunshine_hours < 2.0:
        candidates.append(("short_sunshine", 0.20))
    if snap.apparent_temperature_c is not None and snap.apparent_temperature_c < 15.0:
        candidates.append(("cold", 0.10 + (15 - snap.apparent_temperature_c) / 30.0))
    if not candidates:
        return "default"
    candidates.sort(key=lambda c: c[1], reverse=True)
    return candidates[0][0]


def _recommendation(severity_label: str, snap: WeatherSnapshot) -> Tuple[str, str]:
    """Return (recommendation_id, copy)."""
    sig = _dominant_signal(snap)
    key = f"{severity_label}:{sig}"
    if key in _RECOMMENDATIONS:
        return _RECOMMENDATIONS[key]
    # Fallbacks per severity.
    if severity_label == "high":
        return _RECOMMENDATIONS["high:low_uv"]
    if severity_label == "elevated":
        return _RECOMMENDATIONS["elevated:cloud_cover"]
    if severity_label == "moderate":
        return _RECOMMENDATIONS["moderate:cloud_cover"]
    return _RECOMMENDATIONS["low:default"]


def _mood_modifier(snap: WeatherSnapshot, sad_score: float) -> MoodModifier:
    """Tiny multipliers downstream consumers can apply to expected
    activity levels. Capped within [0.5, 1.1] so a single bad-weather
    day never flatlines a feature.
    """
    base = 1.0 - 0.4 * sad_score
    energy = max(0.5, min(1.1, base + (0.05 if (snap.uv_index or 0) >= 5 else 0)))
    motivation = max(0.5, min(1.1, base))
    sociability = max(0.5, min(1.1, base + (-0.05 if (snap.precipitation_mm or 0) > 5 else 0)))
    return MoodModifier(
        energy=float(energy),
        motivation=float(motivation),
        sociability=float(sociability),
    )


# ── Open-Meteo response → flat snapshots ──────────────────────────────────


def _today_snapshot(meteo: dict) -> WeatherSnapshot:
    current = meteo.get("current") or {}
    daily = meteo.get("daily") or {}
    sunshine_seconds = (daily.get("sunshine_duration") or [None])[0]
    sunshine_hours = (
        sunshine_seconds / 3600.0 if isinstance(sunshine_seconds, (int, float)) else None
    )
    return WeatherSnapshot(
        uv_index=(daily.get("uv_index_max") or [None])[0],
        sunshine_hours=sunshine_hours,
        cloud_cover_pct=current.get("cloudcover"),
        precipitation_mm=(daily.get("precipitation_sum") or [None])[0],
        temperature_c=current.get("temperature_2m"),
        apparent_temperature_c=current.get("apparent_temperature"),
        wind_speed_kmh=(daily.get("windspeed_10m_max") or [None])[0],
    )


def _day_snapshots(meteo: dict, horizon_days: int) -> List[WeatherSnapshot]:
    daily = meteo.get("daily") or {}
    out: List[WeatherSnapshot] = []
    n = min(horizon_days, len(daily.get("time") or []))
    for i in range(n):
        sunshine_seconds = (daily.get("sunshine_duration") or [None])[i]
        sunshine_hours = (
            sunshine_seconds / 3600.0 if isinstance(sunshine_seconds, (int, float)) else None
        )
        # Apparent temp not in daily — use min/max midpoint as a stand-in.
        tmax = (daily.get("temperature_2m_max") or [None])[i]
        tmin = (daily.get("temperature_2m_min") or [None])[i]
        avg_t = (
            ((tmax + tmin) / 2.0) if isinstance(tmax, (int, float)) and isinstance(tmin, (int, float))
            else None
        )
        out.append(WeatherSnapshot(
            uv_index=(daily.get("uv_index_max") or [None])[i],
            sunshine_hours=sunshine_hours,
            cloud_cover_pct=None,  # daily endpoint doesn't supply
            precipitation_mm=(daily.get("precipitation_sum") or [None])[i],
            temperature_c=avg_t,
            apparent_temperature_c=avg_t,
            wind_speed_kmh=(daily.get("windspeed_10m_max") or [None])[i],
        ))
    return out


# ── Public API ──────────────────────────────────────────────────────────────


def mood_context(
    lat: Optional[float] = None, lon: Optional[float] = None,
) -> WeatherMoodContext:
    """Today's weather-mood payload — what the My Summary card binds to."""
    lat_, lon_, label, source = _resolve_location(lat, lon)
    meteo = _fetch_weather(lat_, lon_)
    if meteo is None:
        # Open-Meteo unreachable. Return a neutral structure so the UI
        # still has something to render.
        snap = WeatherSnapshot()
        sad = 0.0
        sev_label, color, icon = _severity(0.0)
        rec_id, rec = _RECOMMENDATIONS["low:default"]
        return WeatherMoodContext(
            location=label,
            latitude=lat_,
            longitude=lon_,
            geocoding_source=source,
            weather=snap,
            sad_risk_score=sad,
            sad_severity_label=sev_label,
            severity_color=color,
            icon_hint=icon,
            mood_modifier=_mood_modifier(snap, sad),
            recommendation=rec,
            recommendation_id=rec_id,
            computed_at=datetime.now(timezone.utc),
            source="fallback",
        )

    snap = _today_snapshot(meteo)
    sad = _sad_risk(snap)
    sev_label, color, icon = _severity(sad)
    rec_id, rec = _recommendation(sev_label, snap)
    return WeatherMoodContext(
        location=label,
        latitude=lat_,
        longitude=lon_,
        geocoding_source=source,
        weather=snap,
        sad_risk_score=sad,
        sad_severity_label=sev_label,
        severity_color=color,
        icon_hint=icon,
        mood_modifier=_mood_modifier(snap, sad),
        recommendation=rec,
        recommendation_id=rec_id,
        computed_at=datetime.now(timezone.utc),
        source="live",
    )


def forecast_risk(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    horizon_days: int = 7,
) -> WeatherForecastResponse:
    """7-day SAD-risk forecast aligned with the Seq2Seq simulation window."""
    horizon_days = max(1, min(horizon_days, 7))
    lat_, lon_, label, _source = _resolve_location(lat, lon)
    meteo = _fetch_weather(lat_, lon_)
    days_out: List[WeatherDayForecast] = []
    if meteo is not None:
        snaps = _day_snapshots(meteo, horizon_days)
        for i, snap in enumerate(snaps):
            sad = _sad_risk(snap)
            sev_label, color, icon = _severity(sad)
            _, rec = _recommendation(sev_label, snap)
            days_out.append(WeatherDayForecast(
                day_offset=i,
                sad_risk_score=sad,
                weather=snap,
                summary=rec,
                severity_color=color,
                icon_hint=icon,
            ))
    return WeatherForecastResponse(
        location=label,
        latitude=lat_,
        longitude=lon_,
        days=days_out,
        horizon_days=horizon_days,
        computed_at=datetime.now(timezone.utc),
        source="live" if days_out else "fallback",
    )
