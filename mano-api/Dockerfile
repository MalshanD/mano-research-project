# =============================================================================
# MANO API — Dockerfile
# Base: python:3.12-slim (CPU-only)
# Heavy ML stack: TensorFlow + PyTorch + transformers + scikit-learn
# NOTE: First build will take 10-20 min and produce a ~8-12 GB image.
#       Subsequent rebuilds are fast (requirements layer is cached).
# =============================================================================

FROM python:3.12-slim

# ---------------------------------------------------------------------------
# System dependencies
# libgomp1     — OpenMP runtime required by TensorFlow and PyTorch
# libglib2.0-0 — GLib required by some ML/data libs
# curl         — used by the Docker healthcheck
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---------------------------------------------------------------------------
# Install Python dependencies BEFORE copying source so this layer is cached
# and only re-runs when requirements.txt changes.
# ---------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Copy application source
# (venv/, __pycache__, .env, tests/ are excluded via .dockerignore)
# ---------------------------------------------------------------------------
COPY . .

# ---------------------------------------------------------------------------
# Runtime configuration
# ---------------------------------------------------------------------------
# Silence TF/oneDNN noise and force UTF-8 — same as .env.example defaults
ENV TF_ENABLE_ONEDNN_OPTS=0 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# ---------------------------------------------------------------------------
# Healthcheck — hits the liveness endpoint every 30s
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# ---------------------------------------------------------------------------
# Single worker: ML models are loaded into process memory at startup.
# Multiple workers would duplicate the entire model footprint per worker.
# ---------------------------------------------------------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
