# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from db.database import engine
# from db.base import Base
# from contextlib import asynccontextmanager
# import torch
# import sys
# import os
# from core.logging import setup_logging, get_logger
# from core.middleware import RequestLoggingMiddleware, ErrorHandlerMiddleware
# from core.health import router as health_router
# from pathlib import Path
# from core.database import create_tables
# from model import *
# from routes import (
#     assesment_type,
#     question,
#     question_choices_route,
#     user_route,
#     question_answer_route,
#     response_route,
#     # chat_route
# )
# from routes.component1 import(
#     simulation_router,
#     patient_router,
#     whatif_router,
#     xai_router,
#     nba_router,
#     sequence_router,
#     uncertainty_router,
#     report_router,
#     digital_twin_router
# )

# # --- IMPORT SERVICES ---
# from lib.component1.risk_service import RiskPredictionService
# from lib.component1.intervention_service import InterventionService
# from lib.component1.timegan_service import TimeGANService
# from lib.component1.ctgan_service import CTGANService

# # Initialize structured logging BEFORE anything else
# setup_logging()
# logger = get_logger("main")

# Base.metadata.create_all(bind=engine)

# app = FastAPI()

# # ── CORS ────────────────────────────────────────────────────────────────────
# # Allow requests from the Vite dev server (and any localhost port during dev).
# app.add_middleware(ErrorHandlerMiddleware)
# app.add_middleware(RequestLoggingMiddleware)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:3000",
#         "http://localhost:5173",
#         "http://127.0.0.1:3000",
#         "http://127.0.0.1:5173",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # ────────────────────────────────────────────────────────────────────────────

# app.include_router(assesment_type.router)
# app.include_router(question.router)
# app.include_router(question_choices_route.router)
# app.include_router(user_route.router)
# app.include_router(question_answer_route.router)
# app.include_router(response_route.router)
# # app.include_router(chat_route.router)

# # --- LIFESPAN MANAGER (STARTUP/SHUTDOWN LOGIC) ---
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """
#     This function runs ONCE before the server starts accepting requests.
#     It is the perfect place to load heavy ML models into memory (RAM/VRAM).
#     """
#     logger.info("startup_begin", message="MANO AI ENGINE: STARTING UP")

#     # Track which models loaded successfully (used by /health endpoint)
#     models_status = {"lstm": False, "simulator": False, "agent": False, "timegan": False, "ctgan": False}

#     # 1. Hardware Detection
#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     app.state.device = device
#     app.state.gpu_enabled = device == "cuda"

#     if device == "cuda":
#         logger.info("gpu_detected", gpu_name=torch.cuda.get_device_name(0))
#     else:
#         logger.warning("no_gpu", message="Running on CPU. Inference will be slower.")

#     # 2. Locate the Models Repository
#     base_dir = Path(__file__).resolve().parent
#     repo_path = base_dir / "models_repo"

#     # 3. Load the Brains into the Singleton Services
#     try:
#         # Load the Hybrid LSTM
#         logger.info("loading_model", model="risk_lstm", path=str(repo_path / "risk_lstm.pth"))
#         risk_svc = RiskPredictionService()
#         risk_svc.load_model(str(repo_path / "risk_lstm.pth"), device)
#         models_status["lstm"] = True
#         logger.info("model_loaded", model="risk_lstm", status="success")
#     except Exception as e:
#         logger.error("model_load_failed", model="risk_lstm", error=str(e))

#     try:
#         # Load the AMISE Simulator & Agent
#         logger.info("loading_model", model="amise_engines")
#         int_svc = InterventionService()
#         int_svc.load_models(
#             sim_path=str(repo_path / "seq2seq_simulator.pth"),
#             agent_path=str(repo_path / "ppo_agent.pth"),
#             device=device
#         )
#         models_status["simulator"] = True
#         models_status["agent"] = True
#         logger.info("model_loaded", model="amise_engines", status="success")
#     except Exception as e:
#         logger.error("model_load_failed", model="amise_engines", error=str(e))

#     try:
#         # Load TimeGAN (Synthetic Wearable Sequence Generator)
#         logger.info("loading_model", model="timegan")
#         timegan_svc = TimeGANService()
#         models_status["timegan"] = timegan_svc.is_loaded()
#         logger.info("model_loaded", model="timegan", status="success" if models_status["timegan"] else "weights_missing")
#     except Exception as e:
#         logger.error("model_load_failed", model="timegan", error=str(e))

#     try:
#         # Load CTGAN (Synthetic Tabular Profile Generator)
#         logger.info("loading_model", model="ctgan")
#         ctgan_svc = CTGANService()
#         models_status["ctgan"] = ctgan_svc.is_loaded()
#         logger.info("model_loaded", model="ctgan", status="success" if models_status["ctgan"] else "pickle_missing")
#     except Exception as e:
#         logger.error("model_load_failed", model="ctgan", error=str(e))

#     # Store status on app.state for the /health endpoint
#     app.state.models_loaded = models_status

#     # 4. Create database tables
#     logger.info("creating_db_tables", message="Initializing database...")
#     await create_tables()
#     logger.info("db_ready", message="Database tables created.")

#     if all(models_status.values()):
#         logger.info("startup_complete", message="All models loaded. System ready.")
#     else:
#         logger.warning("startup_degraded", models_status=models_status,
#                        message="Some models failed to load. Check logs above.")

#     yield  # --- THE SERVER RUNS HERE ---

#     logger.info("shutdown", message="MANO AI ENGINE: SHUTTING DOWN")


# app = FastAPI(
#     title="MANO AI Engine",
#     description="Privacy-Preserving Mental Health Intervention & Simulation API",
#     version="1.0.0",
#     lifespan=lifespan
# )


# @app.get("/")
# async def root_liveness():
#     """
#     Liveness probe. Just confirms the process is alive.
#     For model readiness, use /health instead.
#     """
#     return {
#         "status": "online",
#         "system": "MANO AI Backend",
#         "gpu_enabled": torch.cuda.is_available() and torch.cuda.device_count() > 0
#     }

# app.include_router(health_router)
# app.include_router(
#     simulation_router.router,
#     prefix="/api/v1/simulation",
#     tags=["Simulation & Optimization"]
# )
# app.include_router(
#     patient_router.router,
#     prefix="/api/v1/patients",
#     tags=["Patient Management"]
# )
# app.include_router(
#     whatif_router.router,
#     prefix="/api/v1/whatif",
#     tags=["What-If Lifestyle Simulator"]
# )
# app.include_router(
#     xai_router.router,
#     prefix="/api/v1/xai",
#     tags=["Explainable AI"]
# )
# app.include_router(
#     nba_router.router,
#     prefix="/api/v1/nba",
#     tags=["Next-Best-Action"]
# )
# app.include_router(
#     sequence_router.router,
#     prefix="/api/v1/sequence",
#     tags=["Intervention Sequencing"]
# )
# app.include_router(
#     uncertainty_router.router,
#     prefix="/api/v1/uncertainty",
#     tags=["MC Dropout Uncertainty"]
# )
# app.include_router(
#     report_router.router,
#     prefix="/api/v1/reports",
#     tags=["Clinical Reports"]
# )
# app.include_router(
#     digital_twin_router.router,
#     prefix="/api/v1/twin",
#     tags=["Digital Twin Factory"]
# )
import os
import warnings

# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP ENVIRONMENT CONFIGURATION
# These env vars MUST be set before importing TensorFlow/sklearn to take effect.
# ═══════════════════════════════════════════════════════════════════════════════
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"      # Silence TF oneDNN info messages
os.environ["PYTHONUTF8"] = "1"                  # Force UTF-8 on Windows consoles
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"        # Hide TF INFO/WARNING logs

# Suppress sklearn version-mismatch warnings (models were pickled on an older version;
# safe for inference but should be retrained on the current version when possible).
from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)

import torch
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Internal imports ─────────────────────────────────────────────────────────
from db.database import engine              # Sync SQLAlchemy engine (legacy models)
from db.base import Base                    # Declarative base for sync ORM models
from core.config import settings            # Immutable settings singleton from .env
from core.logging import setup_logging, get_logger
from core.middleware import RequestLoggingMiddleware, ErrorHandlerMiddleware
from core.health import router as health_router
from core.database import create_tables     # Async table creation for new models
from core.errors import register_error_handlers
from lib.infra.cache import get_cache, reset_cache_for_tests  # noqa: F401
from lib.infra.event_bus import init_event_bus
from lib.infra.rate_limit import register_rate_limiter
from lib.infra.scheduler import get_scheduler
from lib.infra.services import services_registry
from model import *  # Registers all ORM models so SQLAlchemy knows every table

# Routes
from routes import (
    assesment_type,
    question,
    question_choices_route,
    user_route,
    question_answer_route,
    response_route,
    chat_route,
    activity_route,
    community_route,
    insights_route,
    dashboard_route,
    therapy_route,
    enhanced_c1_route,
)
from routes.synthetic import (
    simulation_router,
    patient_router,
    whatif_router,
    xai_router,
    nba_router,
    sequence_router,
    uncertainty_router,
    report_router,
    digital_twin_router,
    trajectory_router,
    counterfactual_router,
    narrative_router,
    evidence_router,
    weather_router,
    voice_journal_router,
    ambient_sound_router,
    affirmation_router,
    dashboard_aggregator_router,
    therapy_orchestrator_router,
    reranker_router,
    clinical_passport_router,
    research_cohort_router,
    research_audit_router,
    research_query_router,
    rehearsal_router,
    attribution_router,
    dose_response_router,
    trajectory_alert_router,
    future_self_router,
    weather_v2_router,
    page_bundles_router,
)

# ── Component 1 ML service singletons (loaded once into memory at startup) ───
from lib.synthetic.risk_service import RiskPredictionService      # LSTM risk predictor
from lib.synthetic.intervention_service import InterventionService # Seq2Seq + PPO agent
from lib.synthetic.timegan_service import TimeGANService           # Synthetic wearable data
from lib.synthetic.ctgan_service import CTGANService               # Synthetic tabular profiles

# 1. Initialize structured logging (must happen before any logger.info calls)
setup_logging()
logger = get_logger("main")

# 2. Lifespan Manager — runs once at startup/shutdown (not per-request)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown handler.

    Startup: detects GPU, loads all 5 ML models into memory, creates DB tables,
    initialises cache/event-bus/scheduler. Each step is fault-tolerant — a single
    model failure degrades the system but does NOT prevent boot.
    Shutdown: gracefully closes scheduler, service registry, and cache connections.
    """
    logger.info("startup_begin", message="MANO AI ENGINE: STARTING UP")
    # Track per-model load status; surfaced by the /health readiness probe
    models_status = {"lstm": False, "simulator": False, "agent": False, "timegan": False, "ctgan": False}

    # Auto-detect CUDA GPU; falls back to CPU (slower but functional)
    device = "cuda" if torch.cuda.is_available() and torch.cuda.device_count() > 0 else "cpu"
    app.state.device = device
    app.state.gpu_enabled = device == "cuda"

    if device == "cuda":
        logger.info("gpu_detected", gpu_name=torch.cuda.get_device_name(0))
    else:
        logger.warning("no_gpu", message="Running on CPU. Inference will be slower.")

    base_dir = Path(__file__).resolve().parent
    repo_path = base_dir / "ml_models" / "component1"

    # Load Models
    try:
        risk_svc = RiskPredictionService()
        risk_svc.load_model(str(repo_path / "risk_lstm.pth"), device)
        models_status["lstm"] = True
        logger.info("model_loaded", model="risk_lstm", status="success")
    except Exception as e:
        logger.error("model_load_failed", model="risk_lstm", error=str(e))

    try:
        int_svc = InterventionService()
        int_svc.load_models(
            sim_path=str(repo_path / "seq2seq_simulator.pth"),
            agent_path=str(repo_path / "ppo_agent.pth"),
            device=device
        )
        models_status["simulator"] = True
        models_status["agent"] = True
        logger.info("model_loaded", model="amise_engines", status="success")
    except Exception as e:
        logger.error("model_load_failed", model="amise_engines", error=str(e))

    try:
        logger.info("loading_model", model="timegan")
        timegan_svc = TimeGANService()
        models_status["timegan"] = timegan_svc.is_loaded()
        logger.info("model_loaded", model="timegan", status="success" if models_status["timegan"] else "weights_missing")
    except Exception as e:
        logger.error("model_load_failed", model="timegan", error=str(e))

    try:
        logger.info("loading_model", model="ctgan")
        ctgan_svc = CTGANService()
        models_status["ctgan"] = ctgan_svc.is_loaded()
        logger.info("model_loaded", model="ctgan", status="success" if models_status["ctgan"] else "pickle_missing")
    except Exception as e:
        logger.error("model_load_failed", model="ctgan", error=str(e))

    app.state.models_loaded = models_status
    await create_tables()

    # Create sync tables (db.base.Base)
    import asyncio
    await asyncio.to_thread(Base.metadata.create_all, bind=engine)

    # ── Phase 0 infra: cache, event bus, scheduler ──────────────────────────
    # All three are best-effort; any failure must NOT prevent startup.
    try:
        cache = get_cache()
        cache_ok = await cache.ping()
        app.state.cache_backend = cache.backend_name
        logger.info("cache_ready", backend=cache.backend_name, reachable=cache_ok)
    except Exception as e:  # pragma: no cover
        app.state.cache_backend = "unavailable"
        logger.error("cache_init_failed", error=str(e))

    try:
        bus = await init_event_bus()
        app.state.event_bus_backend = bus.backend_name
        logger.info("event_bus_ready", backend=bus.backend_name)
    except Exception as e:  # pragma: no cover
        app.state.event_bus_backend = "unavailable"
        logger.error("event_bus_init_failed", error=str(e))

    try:
        scheduler = get_scheduler()
        scheduler.start()
        app.state.scheduler_running = scheduler.running
        logger.info("scheduler_ready", running=scheduler.running)

        # Phase 2: pre-warm PubMed evidence cache every 6h. Registers a
        # single interval job; first cache-populate is lazy on first hit.
        try:
            from lib.synthetic.evidence_service import schedule_evidence_refresh
            schedule_evidence_refresh()
            logger.info("evidence_refresh_scheduled")
        except Exception as e:  # pragma: no cover
            logger.warning("evidence_refresh_schedule_failed", error=str(e))
    except Exception as e:  # pragma: no cover
        app.state.scheduler_running = False
        logger.error("scheduler_init_failed", error=str(e))

    if all(models_status.values()):
        logger.info("startup_complete", message="All models loaded. System ready.")
    else:
        logger.warning("startup_degraded", models_status=models_status, message="Some models failed to load. Check logs above.")
        logger.info("startup_complete", message="System ready (degraded mode).")

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("shutdown", message="MANO AI ENGINE: SHUTTING DOWN")
    try:
        get_scheduler().shutdown()
    except Exception as e:  # pragma: no cover
        logger.warning("scheduler_shutdown_failed", error=str(e))
    try:
        await services_registry.close_all()
    except Exception as e:  # pragma: no cover
        logger.warning("services_close_failed", error=str(e))
    try:
        await get_cache().close()
    except Exception as e:  # pragma: no cover
        logger.warning("cache_close_failed", error=str(e))

# 3. Create the single FastAPI application instance
#    The lifespan hook handles all startup/shutdown orchestration.
app = FastAPI(
    title="MANO AI Engine",
    description="Privacy-Preserving Mental Health Intervention & Simulation API",
    version="1.0.0",
    lifespan=lifespan
)

# 4. Middleware stack (order matters — outermost runs first on requests)
#    CORS → RequestLogging → ErrorHandler → route handler
#    Error handlers are registered as exception_handlers (not middleware)
#    so typed errors (MANOAPIError, validation) get a consistent JSON envelope.
register_error_handlers(app)   # Typed JSON error envelope for all exceptions
register_rate_limiter(app)     # Per-endpoint rate limits from settings
app.add_middleware(ErrorHandlerMiddleware)      # Catch-all for unhandled crashes
app.add_middleware(RequestLoggingMiddleware)     # Logs every request with timing
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),   # Configured in .env / config.py
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Include Routers
# Standard Routes
app.include_router(health_router)
app.include_router(assesment_type.router)
app.include_router(question.router)
app.include_router(question_choices_route.router)
app.include_router(user_route.router)
app.include_router(question_answer_route.router)
app.include_router(response_route.router)
app.include_router(chat_route.router)
app.include_router(activity_route.router)
app.include_router(community_route.router)
app.include_router(insights_route.router)  # Phase 2: Enhanced Risk Insights + SHAP + Counterfactuals
app.include_router(dashboard_route.router)  # Phase 3: Mood-Aware Dashboard + Affirmations + Sentiment
app.include_router(therapy_route.router)  # Phase 4: Guided Wellness Session (Flagship Feature)
app.include_router(enhanced_c1_route.router)  # Phase 5: C1 Narrative Engine + PubMed Evidence

# Versioned Synthetic Routes
app.include_router(simulation_router.router, prefix="/api/v1/simulation", tags=["Simulation & Optimization"])
app.include_router(patient_router.router, prefix="/api/v1/patients", tags=["Patient Management"])
app.include_router(whatif_router.router, prefix="/api/v1/whatif", tags=["What-If Lifestyle Simulator"])
app.include_router(xai_router.router, prefix="/api/v1/xai", tags=["Explainable AI"])
app.include_router(nba_router.router, prefix="/api/v1/nba", tags=["Next-Best-Action"])
app.include_router(sequence_router.router, prefix="/api/v1/sequence", tags=["Intervention Sequencing"])
app.include_router(uncertainty_router.router, prefix="/api/v1/uncertainty", tags=["MC Dropout Uncertainty"])
app.include_router(report_router.router, prefix="/api/v1/reports", tags=["Clinical Reports"])
app.include_router(digital_twin_router.router, prefix="/api/v1/twin", tags=["Digital Twin Factory"])
app.include_router(trajectory_router.router, prefix="/api/v1/trajectory", tags=["Multi-Horizon Trajectory"])
app.include_router(counterfactual_router.router, prefix="/api/v1/counterfactual", tags=["Intervention Counterfactuals"])
app.include_router(narrative_router.router, prefix="/api/v1/narrative", tags=["Future-Self Narrative"])
app.include_router(evidence_router.router, prefix="/api/v1/evidence", tags=["PubMed Evidence"])
app.include_router(weather_router.router, prefix="/api/v1/weather", tags=["Weather & Mood Correlation"])
app.include_router(voice_journal_router.router, prefix="/api/v1/voice", tags=["Voice Journal"])
app.include_router(ambient_sound_router.router, prefix="/api/v1/ambient", tags=["Ambient Sound Library"])
app.include_router(affirmation_router.router, prefix="/api/v1/affirmations", tags=["Daily Affirmations"])
app.include_router(dashboard_aggregator_router.router, prefix="/api/v1/dashboard", tags=["Dashboard Intelligence"])
app.include_router(therapy_orchestrator_router.router, prefix="/api/v1/therapy-care", tags=["Care-Path Therapy Orchestrator"])
app.include_router(reranker_router.router, prefix="/api/v1/reranker", tags=["PPO Reranker"])
app.include_router(clinical_passport_router.router, prefix="/api/v1/passport", tags=["Clinical Passport"])

app.include_router(research_cohort_router.router, prefix="/api/v1/research/cohorts", tags=["Research: Cohort Export"])
app.include_router(research_audit_router.router, prefix="/api/v1/research/audit", tags=["Research: Privacy Audit"])
app.include_router(research_query_router.router, prefix="/api/v1/research/query", tags=["Research: Aggregate Query"])

# ── Component-1 architectural-decisions endpoints ──────────────────────────
# The five engines below sit on top of the frozen models without
# replacing any existing route. See docs/C1_ARCHITECTURE_DECISIONS.md.

# Adaptive Intervention Rehearsal — closed-loop multi-day plan engine.
app.include_router(rehearsal_router.router, prefix="/api/v1/rehearsal", tags=["Adaptive Intervention Rehearsal"])

# Outcome Attribution — separates intervention effect from baseline drift.
app.include_router(attribution_router.router, prefix="/api/v1/attribution", tags=["Outcome Attribution"])

# Dose-Response Sweep — finds the patient's personal sweet-spot intensity.
app.include_router(dose_response_router.router, prefix="/api/v1/dose-response", tags=["Dose-Response Sweep"])

# Proactive Trajectory Alerting — multi-horizon LSTM with WATCH/WARNING/CRITICAL tiers.
app.include_router(trajectory_alert_router.router, prefix="/api/v1/trajectory", tags=["Proactive Trajectory Alerting"])

# Future-Self Narrative — Groq-backed with deterministic template fallback.
app.include_router(future_self_router.router, prefix="/api/v1/future-self", tags=["Future-Self Narrative"])

# Consolidated Weather-Mood / SAD — Open-Meteo + ip-api.
app.include_router(weather_v2_router.router, prefix="/api/v1/weather-v2", tags=["Weather-Mood (Consolidated)"])

# Page-bundle aggregator — one bundled endpoint per consumer page.
# Powers the new 6-page nav (My Summary, See My Future, AI Recommendation,
# Digital Twin, Understand My Risk, Guided Therapy Session).
app.include_router(page_bundles_router.router, prefix="/api/v1", tags=["Consumer Page Bundles"])

@app.get("/", tags=["Liveness"])
async def root_liveness():
    """Lightweight liveness probe — confirms the process is alive.
    For full readiness checks (models, DB, cache), use GET /health instead."""
    return {
        "status": "online",
        "system": "MANO AI Backend",
        "gpu_enabled": torch.cuda.is_available() and torch.cuda.device_count() > 0
    }
