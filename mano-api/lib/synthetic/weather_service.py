"""
Open-Meteo Weather Service — Clinically-Grounded SAD Modulation

Fetches real-time environmental data from the completely free Open-Meteo
API (no API key required) and applies a 3-pathway Seasonal Affective
Disorder model to modulate patient vitals.

Biological Pathways Modeled:
  1. Serotonin Deficit  → Low UV + low sunshine → ↓ mood, ↑ stress
  2. Melatonin Excess   → Short daylight → ↑ sleep duration, ↑ fatigue
  3. Circadian Disruption → Daylight deviation from 12h → ↓ sleep quality, ↑ HR

References:
  - Rosenthal et al. (1984) — SAD diagnostic criteria
  - Lam & Levitan (2000) — Pathophysiology of SAD
  - Wirz-Justice (2018) — Light therapy and circadian rhythms

Cache: In-memory TTL cache (6 hours) keyed by city name.
"""
import httpx
import time
import math
from dataclasses import dataclass, field
from typing import Optional, Dict

from core.logging import get_logger

logger = get_logger("weather_service")

BASE_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 6 * 3600  # 6 hours

# ── City Coordinates ─────────────────────────────────
CITY_COORDS = {
    "colombo":      (6.93, 79.85),
    "kandy":        (7.29, 80.63),
    "galle":        (6.03, 80.22),
    "jaffna":       (9.66, 80.00),
    "london":       (51.51, -0.13),
    "new york":     (40.71, -74.01),
    "los angeles":  (34.05, -118.24),
    "chicago":      (41.88, -87.63),
    "tokyo":        (35.68, 139.69),
    "sydney":       (-33.87, 151.21),
    "melbourne":    (-37.81, 144.96),
    "berlin":       (52.52, 13.41),
    "toronto":      (43.65, -79.38),
    "vancouver":    (49.28, -123.12),
    "mumbai":       (19.08, 72.88),
    "delhi":        (28.61, 77.21),
    "singapore":    (1.35, 103.82),
    "stockholm":    (59.33, 18.07),
    "helsinki":      (60.17, 24.94),
    "oslo":         (59.91, 10.75),
    "reykjavik":    (64.15, -21.94),
    "moscow":       (55.76, 37.62),
    "dubai":        (25.20, 55.27),
    "cape town":    (-33.93, 18.42),
    "sao paulo":    (-23.55, -46.63),
    "bangkok":      (13.76, 100.50),
    "seoul":        (37.57, 126.98),
    "paris":        (48.86, 2.35),
    "amsterdam":    (52.37, 4.90),
}

# Open-Meteo daily fields we request (all free)
OPEN_METEO_DAILY_FIELDS = ",".join([
    "uv_index_max",
    "sunshine_duration",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_mean",
    "precipitation_hours",
    "daylight_duration",
    "windspeed_10m_max",
])


# ── Data Classes ─────────────────────────────────────

@dataclass
class SADPathways:
    """
    Three independent biological pathways affected by environmental factors.
    Each score ranges [0, 1] where 0 = no impact, 1 = maximum impact.
    """
    serotonin_deficit: float = 0.0
    melatonin_excess: float = 0.0
    circadian_disruption: float = 0.0

    @property
    def composite_sad(self) -> float:
        """Weighted composite SAD intensity [0, 1]."""
        return (
            0.45 * self.serotonin_deficit +
            0.30 * self.melatonin_excess +
            0.25 * self.circadian_disruption
        )

    def to_dict(self) -> dict:
        return {
            "serotonin_deficit": round(self.serotonin_deficit, 3),
            "melatonin_excess": round(self.melatonin_excess, 3),
            "circadian_disruption": round(self.circadian_disruption, 3),
            "composite_sad": round(self.composite_sad, 3),
        }


@dataclass
class WeatherContext:
    """Environmental context for a location and date."""
    city: str
    latitude: float
    longitude: float

    # Primary measurements
    temperature_max_c: float = 28.0
    temperature_min_c: float = 22.0
    uv_index_max: float = 6.0
    sunshine_hours: float = 10.0
    daylight_hours: float = 12.0
    humidity_pct: float = 70.0
    precipitation_hours: float = 0.0
    wind_speed_max_kmh: float = 10.0

    # Computed pathways
    pathways: SADPathways = field(default_factory=SADPathways)

    @property
    def sad_intensity(self) -> float:
        """Legacy property — returns composite SAD for backward compat."""
        return self.pathways.composite_sad

    @property
    def temperature_c(self) -> float:
        """Legacy property — returns max temp for backward compat."""
        return self.temperature_max_c


# ── Service ──────────────────────────────────────────

class WeatherService:
    """Fetches environmental data and computes clinically-grounded SAD modulation."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
            cls._instance._client = httpx.Client(timeout=5.0)
        return cls._instance

    # ── Fetch ────────────────────────────────────────

    def get_weather(self, city: str = "colombo") -> WeatherContext:
        """
        Get current weather context for a city.
        Returns cached data if available and fresh, otherwise fetches from API.
        """
        city_lower = city.lower().strip()

        # Check cache
        if city_lower in self._cache:
            data, ts = self._cache[city_lower]
            if time.time() - ts < CACHE_TTL_SECONDS:
                logger.info("weather_cache_hit", city=city_lower)
                return data

        # Resolve coordinates
        if city_lower in CITY_COORDS:
            lat, lon = CITY_COORDS[city_lower]
        else:
            lat, lon = CITY_COORDS["colombo"]
            logger.warning("city_not_found", city=city_lower, fallback="colombo")

        # Fetch from Open-Meteo
        try:
            resp = self._client.get(BASE_URL, params={
                "latitude": lat,
                "longitude": lon,
                "daily": OPEN_METEO_DAILY_FIELDS,
                "timezone": "auto",
                "forecast_days": 1,
            })
            resp.raise_for_status()
            raw = resp.json()
            daily = raw.get("daily", {})

            # Parse all fields with safe defaults
            uv_max        = _safe_first(daily.get("uv_index_max"), 3.0)
            sunshine_sec  = _safe_first(daily.get("sunshine_duration"), 36000)
            temp_max      = _safe_first(daily.get("temperature_2m_max"), 28.0)
            temp_min      = _safe_first(daily.get("temperature_2m_min"), 22.0)
            humidity      = _safe_first(daily.get("relative_humidity_2m_mean"), 70.0)
            precip_hrs    = _safe_first(daily.get("precipitation_hours"), 0.0)
            daylight_sec  = _safe_first(daily.get("daylight_duration"), 43200)
            wind_max      = _safe_first(daily.get("windspeed_10m_max"), 10.0)

            sunshine_hrs = sunshine_sec / 3600.0
            daylight_hrs = daylight_sec / 3600.0

            # Compute SAD pathways
            pathways = self._compute_pathways(
                uv_max=uv_max,
                sunshine_hrs=sunshine_hrs,
                daylight_hrs=daylight_hrs,
                temp_max=temp_max,
                precip_hrs=precip_hrs,
                wind_max=wind_max,
                humidity=humidity,
            )

            weather = WeatherContext(
                city=city_lower,
                latitude=lat,
                longitude=lon,
                temperature_max_c=temp_max,
                temperature_min_c=temp_min,
                uv_index_max=uv_max,
                sunshine_hours=sunshine_hrs,
                daylight_hours=daylight_hrs,
                humidity_pct=humidity,
                precipitation_hours=precip_hrs,
                wind_speed_max_kmh=wind_max,
                pathways=pathways,
            )

            self._cache[city_lower] = (weather, time.time())
            logger.info(
                "weather_fetched", city=city_lower,
                uv=uv_max, sunshine_h=round(sunshine_hrs, 1),
                daylight_h=round(daylight_hrs, 1), temp=temp_max,
                sad_composite=round(pathways.composite_sad, 3),
            )
            return weather

        except Exception as e:
            logger.error("weather_fetch_failed", city=city_lower, error=str(e))
            # Graceful fallback: neutral tropical (minimal SAD impact)
            return WeatherContext(
                city=city_lower, latitude=lat, longitude=lon,
                pathways=SADPathways(0.1, 0.05, 0.05),
            )

    # ── SAD Pathway Computation ──────────────────────

    @staticmethod
    def _compute_pathways(
        uv_max: float,
        sunshine_hrs: float,
        daylight_hrs: float,
        temp_max: float,
        precip_hrs: float,
        wind_max: float,
        humidity: float,
    ) -> SADPathways:
        """
        Compute the 3 independent SAD biological pathways.

        Pathway 1: SEROTONIN DEFICIT
          Serotonin production is directly linked to sunlight exposure.
          Low UV + low sunshine → reduced serotonin → depressed mood,
          increased appetite (carb craving), and social withdrawal.
          Rain and high humidity further reduce effective light exposure.

        Pathway 2: MELATONIN EXCESS
          Short daylight triggers excess melatonin production.
          Results in hypersomnia, fatigue, and low energy.
          Cold temperatures amplify the "hibernation" response.

        Pathway 3: CIRCADIAN DISRUPTION
          Maximum disruption when daylight deviates from the 12h equinox.
          Extreme northern/southern latitudes in winter experience this.
          Irregular light patterns → fragmented sleep, HR variability.
        """

        # ── Pathway 1: Serotonin Deficit [0, 1] ──
        # UV contribution (UV < 2 = very low serotonin stimulation)
        uv_factor = 1.0 - min(uv_max / 8.0, 1.0)

        # Sunshine contribution (< 4h sunshine = severe deficit)
        sun_factor = 1.0 - min(sunshine_hrs / 12.0, 1.0)

        # Rain reduces effective outdoor light exposure
        rain_penalty = min(precip_hrs / 10.0, 0.3)  # up to +0.3

        # High humidity + overcast = grey skies = less effective light
        humidity_penalty = max(0.0, (humidity - 70.0) / 100.0) * 0.15

        serotonin_deficit = min(1.0, max(0.0,
            0.55 * uv_factor + 0.30 * sun_factor + rain_penalty + humidity_penalty
        ))

        # ── Pathway 2: Melatonin Excess [0, 1] ──
        # Core driver: short daylight hours (biological trigger)
        daylight_deficit = 1.0 - min(daylight_hrs / 16.0, 1.0)

        # Cold temperatures amplify the hibernation response
        cold_factor = max(0.0, (15.0 - temp_max) / 30.0)  # ramps from 15°C down

        melatonin_excess = min(1.0, max(0.0,
            0.70 * daylight_deficit + 0.30 * cold_factor
        ))

        # ── Pathway 3: Circadian Disruption [0, 1] ──
        # Maximum disruption at extreme daylight deviation from 12h
        daylight_deviation = abs(daylight_hrs - 12.0) / 12.0

        # Strong wind + rain = less outdoor time = less zeitgeber exposure
        outdoor_barrier = min(1.0, (wind_max / 50.0) + (precip_hrs / 12.0)) * 0.3

        circadian_disruption = min(1.0, max(0.0,
            0.70 * daylight_deviation + outdoor_barrier
        ))

        return SADPathways(
            serotonin_deficit=round(serotonin_deficit, 4),
            melatonin_excess=round(melatonin_excess, 4),
            circadian_disruption=round(circadian_disruption, 4),
        )

    # ── Vitals Modulation ────────────────────────────

    @staticmethod
    def modulate_vitals(vitals_row: list, weather: "WeatherContext") -> list:
        """
        Apply clinically-grounded SAD modulation to a single day's vitals.

        Input:  [sleep_hours, sleep_quality, heart_rate, stress_level]
        Output: [modulated_sleep_h, modulated_quality, modulated_hr, modulated_stress]

        Effects by pathway:

        SEROTONIN DEFICIT (mood pathway):
          - Stress ↑ up to +0.15 (depressed mood, irritability)
          - Sleep quality ↓ up to -20% (mood-related insomnia despite fatigue)
          - Heart rate ↑ up to +5 bpm (autonomic sympathetic response)

        MELATONIN EXCESS (sleep/energy pathway):
          - Sleep duration ↑ up to +1.5h (hypersomnia)
          - Sleep quality ↓ up to -10% (excess sleep ≠ restorative sleep)
          - Stress ↑ up to +0.05 (fatigue-induced emotional reactivity)

        CIRCADIAN DISRUPTION (rhythm pathway):
          - Sleep quality ↓ up to -15% (fragmented, unrestorative sleep)
          - Heart rate ↑ up to +3 bpm (autonomic instability)
          - Sleep duration shows variability (already modeled by TimeGAN noise)
        """
        sleep_h, quality, hr, stress = vitals_row
        p = weather.pathways

        # ── Sleep Duration (primarily melatonin-driven) ──
        sleep_h += 1.5 * p.melatonin_excess  # hypersomnia
        sleep_h = min(sleep_h, 12.0)

        # ── Sleep Quality (all three pathways degrade it) ──
        quality *= (1.0 - 0.20 * p.serotonin_deficit)    # mood-related
        quality *= (1.0 - 0.10 * p.melatonin_excess)      # non-restorative excess sleep
        quality *= (1.0 - 0.15 * p.circadian_disruption)  # fragmented rhythm
        quality = max(0.0, quality)

        # ── Heart Rate (serotonin + circadian) ──
        hr += 5.0 * p.serotonin_deficit * 0.6     # sympathetic nervous response
        hr += 3.0 * p.circadian_disruption * 0.4   # autonomic instability
        hr = min(hr, 115.0)

        # ── Stress Level (primarily serotonin, some melatonin) ──
        stress += 0.15 * p.serotonin_deficit       # mood-driven stress elevation
        stress += 0.05 * p.melatonin_excess         # fatigue → irritability
        stress = min(stress, 1.0)

        return [sleep_h, quality, hr, stress]

    # ── Utilities ────────────────────────────────────

    def get_available_cities(self) -> list:
        """Return list of known cities."""
        return sorted(CITY_COORDS.keys())


def _safe_first(arr, default):
    """Safely extract first element from Open-Meteo response array."""
    if arr and len(arr) > 0 and arr[0] is not None:
        return arr[0]
    return default
