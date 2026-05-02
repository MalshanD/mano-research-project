"""
Weather-mood correlation service.

Goal
----
Given a patient's daily mood/stress history (≥5 days), pull the matching
historical daily weather for their location and compute Pearson correlations
per weather feature. Surface the strongest driver so the frontend can say
"your mood tracks daylight hours this week" rather than dumping a matrix.

Data sources
------------
* Open-Meteo Historical Forecast Archive — https://archive-api.open-meteo.com
  * Completely free, no API key, no trial.
  * Daily granularity matches the patient's self-reported mood cadence.
* Open-Meteo Geocoding — for unknown cities. Also free, no key.

Correctness caveats (surfaced in the response notes)
----------------------------------------------------
* Single-patient, short-window Pearson is inherently noisy. We label
  ``|r| < 0.2`` as *negligible* so the UI doesn't narrate spurious hits.
* We align on local date. Timezones beyond the city's will produce phase
  errors; Open-Meteo's ``timezone=auto`` handles the city side.
* Correlation is not causation — this is descriptive, not prescriptive.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import OPEN_METEO_GEOCODE_URL
from lib.infra.cache import get_cache
from lib.synthetic.weather_service import CITY_COORDS

logger = logging.getLogger(__name__)

# Open-Meteo's historical archive endpoint. Kept module-local rather than
# pushed into core.config because this is the only consumer.
_OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

_ARCHIVE_DAILY_FIELDS = ",".join([
    "uv_index_max",
    "sunshine_duration",
    "daylight_duration",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_mean",
    "precipitation_hours",
    "windspeed_10m_max",
])

_FEATURE_LABELS: Dict[str, str] = {
    "uv_index_max": "peak UV index",
    "sunshine_hours": "sunshine duration",
    "daylight_hours": "daylight duration",
    "temperature_max_c": "peak temperature",
    "temperature_min_c": "low temperature",
    "humidity_pct": "humidity",
    "precipitation_hours": "precipitation",
    "wind_speed_max_kmh": "wind speed",
}

_CACHE_TTL_SECONDS = 6 * 3600
_GEOCODE_TIMEOUT = 6.0
_ARCHIVE_TIMEOUT = 10.0


@dataclass(frozen=True)
class _DailyWeather:
    """One day of historical weather, aligned to the patient's mood date."""
    date: date
    uv_index_max: float
    sunshine_hours: float
    daylight_hours: float
    temperature_max_c: float
    temperature_min_c: float
    humidity_pct: float
    precipitation_hours: float
    wind_speed_max_kmh: float


# ─── Geocoding ────────────────────────────────────────────────────────────────

async def _resolve_coordinates(
    *, city: Optional[str], latitude: Optional[float], longitude: Optional[float],
) -> Tuple[str, float, float, List[str]]:
    """Resolve (city, lat, lon) from request inputs. Returns (name, lat, lon, notes)."""
    notes: List[str] = []

    if latitude is not None and longitude is not None:
        return (city or f"{latitude:.3f},{longitude:.3f}", latitude, longitude, notes)

    if city:
        key = city.lower().strip()
        if key in CITY_COORDS:
            lat, lon = CITY_COORDS[key]
            return key, lat, lon, notes

        # Fallback to Open-Meteo geocoding — free, no key.
        try:
            async with httpx.AsyncClient(timeout=_GEOCODE_TIMEOUT) as client:
                resp = await client.get(
                    OPEN_METEO_GEOCODE_URL,
                    params={"name": city, "count": 1, "language": "en", "format": "json"},
                )
            if resp.status_code == 200:
                results = (resp.json().get("results") or [])
                if results:
                    hit = results[0]
                    return (
                        str(hit.get("name") or city).lower(),
                        float(hit.get("latitude")),
                        float(hit.get("longitude")),
                        notes,
                    )
                notes.append(f"Geocoder returned no match for '{city}'")
            else:
                notes.append(f"Geocoder HTTP {resp.status_code}")
        except Exception as exc:
            notes.append(f"Geocoder error: {exc}")

    # Final fallback — default coordinates so the downstream call never crashes.
    fallback_city, (lat, lon) = "colombo", CITY_COORDS["colombo"]
    notes.append(f"Using default location ({fallback_city}) because resolution failed.")
    return fallback_city, lat, lon, notes


# ─── Archive fetch ────────────────────────────────────────────────────────────

async def _fetch_archive(
    *, latitude: float, longitude: float, start: date, end: date,
) -> List[_DailyWeather]:
    """Fetch daily historical weather. Raises if the archive call fails."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": _ARCHIVE_DAILY_FIELDS,
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=_ARCHIVE_TIMEOUT) as client:
        resp = await client.get(_OPEN_METEO_ARCHIVE_URL, params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"Open-Meteo archive HTTP {resp.status_code}: {resp.text[:200]}")

    daily = resp.json().get("daily", {}) or {}
    dates = daily.get("time") or []
    out: List[_DailyWeather] = []

    def _pick(key: str, idx: int, default: float) -> float:
        series = daily.get(key) or []
        if idx < len(series) and series[idx] is not None:
            return float(series[idx])
        return default

    for i, d in enumerate(dates):
        try:
            day = date.fromisoformat(d)
        except Exception:
            continue
        out.append(_DailyWeather(
            date=day,
            uv_index_max=_pick("uv_index_max", i, 0.0),
            sunshine_hours=_pick("sunshine_duration", i, 0.0) / 3600.0,
            daylight_hours=_pick("daylight_duration", i, 0.0) / 3600.0,
            temperature_max_c=_pick("temperature_2m_max", i, 0.0),
            temperature_min_c=_pick("temperature_2m_min", i, 0.0),
            humidity_pct=_pick("relative_humidity_2m_mean", i, 0.0),
            precipitation_hours=_pick("precipitation_hours", i, 0.0),
            wind_speed_max_kmh=_pick("windspeed_10m_max", i, 0.0),
        ))
    return out


# ─── Pearson + interpretation ────────────────────────────────────────────────

def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """Vanilla Pearson r. Returns None for < 3 samples or zero variance."""
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    denom = (var_x * var_y) ** 0.5
    return cov / denom


def _strength_label(r: float) -> str:
    abs_r = abs(r)
    if abs_r >= 0.6:
        return "strong"
    if abs_r >= 0.4:
        return "moderate"
    if abs_r >= 0.2:
        return "weak"
    return "negligible"


def _direction_label(r: float) -> str:
    if r > 0.05:
        return "positive"
    if r < -0.05:
        return "negative"
    return "none"


def _interpretation(feature: str, r: float, n: int) -> str:
    label = _strength_label(r)
    direction = _direction_label(r)
    friendly = _FEATURE_LABELS.get(feature, feature)
    if label == "negligible":
        return (
            f"No meaningful relationship between your mood and {friendly} in the "
            f"last {n} days."
        )
    arrow = "rises with" if direction == "positive" else "falls as"
    return (
        f"{label.capitalize()} {direction} link: your reported score {arrow} "
        f"{friendly} (r={r:+.2f}, n={n})."
    )


def _feature_series(daily: List[_DailyWeather]) -> Dict[str, List[float]]:
    """Pack per-feature series aligned in the input order."""
    return {
        "uv_index_max": [d.uv_index_max for d in daily],
        "sunshine_hours": [d.sunshine_hours for d in daily],
        "daylight_hours": [d.daylight_hours for d in daily],
        "temperature_max_c": [d.temperature_max_c for d in daily],
        "temperature_min_c": [d.temperature_min_c for d in daily],
        "humidity_pct": [d.humidity_pct for d in daily],
        "precipitation_hours": [d.precipitation_hours for d in daily],
        "wind_speed_max_kmh": [d.wind_speed_max_kmh for d in daily],
    }


def _correlations(
    feature_series: Dict[str, List[float]], target: List[float],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    n = len(target)
    for feature, values in feature_series.items():
        r = _pearson(values, target)
        if r is None:
            continue
        rows.append({
            "feature": feature,
            "pearson_r": round(r, 4),
            "n_samples": n,
            "strength": _strength_label(r),
            "direction": _direction_label(r),
            "interpretation": _interpretation(feature, r, n),
        })
    # Sort by |r| descending so the dominant driver is first.
    rows.sort(key=lambda row: abs(row["pearson_r"]), reverse=True)
    return rows


# ─── Public entry point ───────────────────────────────────────────────────────

async def correlate_weather_mood(
    *,
    mood_history: List[Dict[str, Any]],
    city: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
) -> Dict[str, Any]:
    """Compute mood↔weather Pearson correlations for the requested window.

    ``mood_history`` items are expected to have ``{date, mood_score, stress_score?}``
    entries; the schema normaliser hands them in as dicts so this function
    stays decoupled from Pydantic specifics.
    """
    notes: List[str] = []

    city_name, lat, lon, geocode_notes = await _resolve_coordinates(
        city=city, latitude=latitude, longitude=longitude,
    )
    notes.extend(geocode_notes)

    # Index mood by date for fast alignment.
    mood_by_date: Dict[date, Dict[str, Any]] = {
        m["date"]: m for m in mood_history if "date" in m
    }
    if not mood_by_date:
        return {
            "city": city_name, "latitude": lat, "longitude": lon,
            "date_range": "", "n_samples": 0,
            "mood_correlations": [], "stress_correlations": None,
            "dominant_mood_driver": None, "dominant_stress_driver": None,
            "source": "fallback",
            "notes": notes + ["Empty mood history after parsing."],
        }

    start = min(mood_by_date.keys())
    end = max(mood_by_date.keys())

    # Cache lookup — keyed on (coords, date range, mood hash).
    cache = get_cache()
    mood_hash = hashlib.sha256(
        json.dumps(
            [(d.isoformat(), float(m["mood_score"]), float(m.get("stress_score") or -1))
             for d, m in sorted(mood_by_date.items())],
            sort_keys=True,
        ).encode("utf-8"),
    ).hexdigest()[:16]
    cache_key = f"weather_mood:v1:{lat:.3f}:{lon:.3f}:{start}:{end}:{mood_hash}"
    try:
        hit = await cache.get(cache_key)
    except Exception:  # pragma: no cover
        hit = None
    if hit:
        hit["source"] = "cached"
        return hit

    # Archive fetch.
    t0 = time.perf_counter()
    try:
        daily = await _fetch_archive(latitude=lat, longitude=lon, start=start, end=end)
    except Exception as exc:
        logger.info("weather_mood_archive_failed", extra={"error": str(exc)})
        return {
            "city": city_name, "latitude": lat, "longitude": lon,
            "date_range": f"{start} → {end}", "n_samples": 0,
            "mood_correlations": [], "stress_correlations": None,
            "dominant_mood_driver": None, "dominant_stress_driver": None,
            "source": "fallback",
            "notes": notes + [f"Archive fetch failed: {exc}"],
        }

    # Align weather to mood dates. Missing days on either side are dropped.
    aligned: List[_DailyWeather] = []
    mood_scores: List[float] = []
    stress_scores: List[float] = []
    has_stress = False
    for d in daily:
        m = mood_by_date.get(d.date)
        if m is None:
            continue
        aligned.append(d)
        mood_scores.append(float(m["mood_score"]))
        if m.get("stress_score") is not None:
            has_stress = True
            stress_scores.append(float(m["stress_score"]))
        else:
            stress_scores.append(float("nan"))

    n = len(aligned)
    if n < 3:
        notes.append(
            f"Aligned only {n} days — need at least 3 for a correlation. "
            "Check that mood dates fall within the archive's coverage."
        )
        return {
            "city": city_name, "latitude": lat, "longitude": lon,
            "date_range": f"{start} → {end}", "n_samples": n,
            "mood_correlations": [], "stress_correlations": None,
            "dominant_mood_driver": None, "dominant_stress_driver": None,
            "source": "live", "notes": notes,
        }

    series = _feature_series(aligned)
    mood_rows = _correlations(series, mood_scores)

    stress_rows: Optional[List[Dict[str, Any]]] = None
    dominant_stress = None
    if has_stress:
        # Filter out nan days for stress — each feature/stress pair only uses
        # the days where stress was reported.
        stress_pairs: Dict[str, List[float]] = {k: [] for k in series}
        clean_stress: List[float] = []
        for i, s in enumerate(stress_scores):
            if s != s:  # NaN check
                continue
            clean_stress.append(s)
            for k, v in series.items():
                stress_pairs[k].append(v[i])
        if len(clean_stress) >= 3:
            stress_rows = _correlations(stress_pairs, clean_stress)
            if stress_rows:
                dominant_stress = stress_rows[0]["feature"]

    dominant_mood = mood_rows[0]["feature"] if mood_rows else None

    if n < 7:
        notes.append(
            f"Only {n} aligned days — interpret with caution. At least 14 days "
            "produces more stable estimates."
        )

    latency_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "weather_mood_computed",
        extra={"city": city_name, "n": n, "latency_ms": round(latency_ms, 1)},
    )

    result = {
        "city": city_name, "latitude": lat, "longitude": lon,
        "date_range": f"{start} → {end}", "n_samples": n,
        "mood_correlations": mood_rows,
        "stress_correlations": stress_rows,
        "dominant_mood_driver": dominant_mood,
        "dominant_stress_driver": dominant_stress,
        "source": "live",
        "notes": notes,
    }
    try:
        await cache.set(cache_key, result, ttl=_CACHE_TTL_SECONDS)
    except Exception:  # pragma: no cover
        pass
    return result


# ─── Thin forecast-envelope wrapper ───────────────────────────────────────────

def current_forecast(city: str) -> Dict[str, Any]:
    """Fetch the current-day forecast via the legacy ``WeatherService`` and
    wrap it in the Phase-2 source-tag envelope shape.

    The legacy service is synchronous and already caches per-city for 6h; we
    just re-shape its output.
    """
    # Deferred import avoids pulling the legacy singleton at module load.
    from lib.synthetic.weather_service import WeatherService

    svc = WeatherService()
    ctx = svc.get_weather(city)
    return {
        "city": ctx.city,
        "latitude": ctx.latitude,
        "longitude": ctx.longitude,
        "temperature_max_c": ctx.temperature_max_c,
        "temperature_min_c": ctx.temperature_min_c,
        "uv_index_max": ctx.uv_index_max,
        "sunshine_hours": ctx.sunshine_hours,
        "daylight_hours": ctx.daylight_hours,
        "humidity_pct": ctx.humidity_pct,
        "precipitation_hours": ctx.precipitation_hours,
        "wind_speed_max_kmh": ctx.wind_speed_max_kmh,
        "sad_composite": ctx.pathways.composite_sad,
        "source": "live",
        "provider": "open-meteo",
        "notes": [],
    }
