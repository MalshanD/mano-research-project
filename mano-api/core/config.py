"""
Centralised runtime configuration for the MANO backend.

Design goals
------------
* A single, immutable ``settings`` singleton that captures every tunable knob.
* Every external URL lives here (never hard-coded in service modules) so we can
  point a staging environment at sandboxes, or swap regional endpoints without
  touching business logic.
* Optional-by-default: the app MUST boot and serve a degraded-but-valid
  response for every endpoint even with zero third-party API keys configured.
  Only ``DATABASE_URL`` is required.
* The module is safe to import at module-scope from anywhere — it touches no
  network, opens no files, and performs no heavy work.

Keep this file *boring*. Anything more exciting than env-parsing belongs in
``lib/infra`` (cache, event bus, security, rate limiting, etc.).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from dotenv import load_dotenv

# Load .env once at import time. Subsequent ``os.getenv`` calls work normally.
load_dotenv()


# --- helpers --------------------------------------------------------------

def _env(name: str, default: str = "") -> str:
    """Return an env var stripped of whitespace; empty string if unset."""
    return (os.getenv(name) or default).strip()


def _env_optional(name: str) -> Optional[str]:
    """Return an env var or ``None`` if unset / empty."""
    value = _env(name)
    return value or None


def _env_list(name: str, default: str) -> List[str]:
    raw = _env(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "y", "t"}


# --- External API base URLs ----------------------------------------------
#
# Canonical endpoints. Service classes import *from here* rather than
# hard-coding strings. A future self-hosted NCBI proxy (for example) only
# requires a change in this file.

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
HUGGINGFACE_BASE_URL = "https://api-inference.huggingface.co/models"

PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

AFFIRMATIONS_URL = "https://www.affirmations.dev/"
ZENQUOTES_URL = "https://zenquotes.io/api/random"

FREESOUND_BASE_URL = "https://freesound.org/apiV2"
YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"
IP_API_URL = "http://ip-api.com/json"


# --- Settings dataclass --------------------------------------------------

@dataclass(frozen=True)
class Settings:
    # Core runtime
    database_url: str
    log_level: str = "INFO"
    cors_origins: Tuple[str, ...] = field(default_factory=tuple)
    environment: str = "development"  # development | staging | production

    # Cache backend
    redis_url: Optional[str] = None

    # Event bus
    event_bus_backend: str = "inprocess"  # inprocess | kafka
    kafka_bootstrap_servers: Optional[str] = None

    # Rate limiting
    rate_limit_default: str = "100/minute"
    rate_limit_ml: str = "20/minute"
    rate_limit_llm: str = "10/minute"

    # LLM API keys (all optional)
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None

    # Research / evidence
    ncbi_api_key: Optional[str] = None

    # Ambient audio
    freesound_api_key: Optional[str] = None
    youtube_api_key: Optional[str] = None

    # Email (SMTP for researcher batch jobs)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_address: Optional[str] = None

    # Health & paths
    ml_models_dir: str = "ml_models"

    @property
    def has_redis(self) -> bool:
        return bool(self.redis_url)

    @property
    def has_kafka(self) -> bool:
        return self.event_bus_backend == "kafka" and bool(self.kafka_bootstrap_servers)

    @property
    def has_smtp(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_address)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


def load_settings() -> Settings:
    database_url = _env("DATABASE_URL", "mysql+pymysql://user:password@localhost:3306/mano_db")

    return Settings(
        database_url=database_url,
        log_level=_env("LOG_LEVEL", "INFO"),
        cors_origins=tuple(_env_list(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,"
            "http://127.0.0.1:3000,http://127.0.0.1:5173",
        )),
        environment=_env("ENVIRONMENT", "development"),

        redis_url=_env_optional("REDIS_URL"),

        event_bus_backend=_env("EVENT_BUS_BACKEND", "inprocess").lower(),
        kafka_bootstrap_servers=_env_optional("KAFKA_BOOTSTRAP_SERVERS"),

        rate_limit_default=_env("RATE_LIMIT_DEFAULT", "100/minute"),
        rate_limit_ml=_env("RATE_LIMIT_ML", "20/minute"),
        rate_limit_llm=_env("RATE_LIMIT_LLM", "10/minute"),

        gemini_api_key=_env_optional("GEMINI_API_KEY"),
        groq_api_key=_env_optional("GROQ_API_KEY"),
        huggingface_api_key=_env_optional("HUGGINGFACE_API_KEY"),

        ncbi_api_key=_env_optional("NCBI_API_KEY"),

        freesound_api_key=_env_optional("FREESOUND_API_KEY"),
        youtube_api_key=_env_optional("YOUTUBE_API_KEY"),

        smtp_host=_env_optional("SMTP_HOST"),
        smtp_port=_env_int("SMTP_PORT", 587),
        smtp_user=_env_optional("SMTP_USER"),
        smtp_password=_env_optional("SMTP_PASSWORD"),
        smtp_from_address=_env_optional("SMTP_FROM_ADDRESS"),

        ml_models_dir=_env("ML_MODELS_DIR", "ml_models"),
    )


settings: Settings = load_settings()


# Backwards-compatibility: some legacy modules import DATABASE_URL directly.
DATABASE_URL = settings.database_url
