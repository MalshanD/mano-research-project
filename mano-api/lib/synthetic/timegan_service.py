"""
TimeGAN Inference Service

Loads the trained TimeGAN checkpoint and exposes component1 7-day
wearable sequence generation at the backend service layer.

Output signals (normalized 0→1):
  [Sleep Duration, Quality of Sleep, Heart Rate, Stress Level]

Usage:
  service = TimeGANService()
  sequences = service.generate(num_samples=50)   # (50, 7, 4) numpy
  denorm    = service.generate_denormalized(10)   # real-world units
"""
import torch
import numpy as np
from pathlib import Path

from ml_models.component1.timegan_model_Def import (
    TimeGAN,
    TIMEGAN_DEFAULTS,
    SIGNAL_NAMES,
)
from core.logging import get_logger

logger = get_logger("timegan_service")

# ── Approximate real-world ranges observed in training data ──
# These are used to de-normalize TimeGAN output from [0, 1]
DENORM_RANGES = {
    "Sleep Duration":    {"min": 4.0,  "max": 9.0},   # hours
    "Quality of Sleep":  {"min": 0.0,  "max": 1.0},   # already 0-1
    "Heart Rate":        {"min": 55.0, "max": 100.0},  # bpm
    "Stress Level":      {"min": 0.0,  "max": 1.0},   # already 0-1
}

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "ml_models" / "component1" / "timegan_final.pth"


class TimeGANService:
    """Wraps the TimeGAN model for inference."""

    _instance = None

    def __new__(cls):
        """Singleton — load model once, reuse across requests."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.device = "cuda" if torch.cuda.is_available() and torch.cuda.device_count() > 0 else "cpu"
        cfg = TIMEGAN_DEFAULTS

        self.seq_len = cfg["seq_len"]
        self.n_signals = cfg["n_signals"]

        # Build the model
        self.model = TimeGAN(
            feature_dim=cfg["n_signals"],
            hidden_dim=cfg["hidden_dim"],
            num_layers=cfg["num_layers"],
            device=self.device,
        )

        # Load trained weights
        if MODEL_PATH.exists():
            state_dict = torch.load(MODEL_PATH, map_location=self.device, weights_only=False)
            self.model.load_state_dict(state_dict)
            logger.info("timegan_loaded", path=str(MODEL_PATH), device=self.device)
        else:
            logger.warning(
                "timegan_not_found",
                path=str(MODEL_PATH),
                msg="Using random weights — generation will not be meaningful",
            )

        self.model.eval()
        self._initialized = True

    # ────────────────────────────────────────────────

    def generate(self, num_samples: int = 100, batch_size: int = 100) -> np.ndarray:
        """
        Generate component1 wearable sequences.

        Returns:
            np.ndarray of shape (num_samples, 7, 4)  —  values in [0, 1]
        """
        generated = []

        with torch.no_grad():
            for i in range(0, num_samples, batch_size):
                current_batch = min(batch_size, num_samples - i)

                # 1. Random noise seed
                Z = torch.rand(
                    (current_batch, self.seq_len, self.n_signals),
                    dtype=torch.float32,
                ).to(self.device)

                # 2. Generator → raw latent
                E_hat = self.model.forward_generator(Z)

                # 3. Supervisor → temporally coherent latent
                H_hat = self.model.forward_supervisor(E_hat)

                # 4. Recovery → readable features
                X_hat = self.model.forward_recovery(H_hat)

                generated.append(X_hat.cpu().numpy())

        result = np.concatenate(generated, axis=0)
        logger.info("timegan_generated", num_samples=num_samples, shape=str(result.shape))
        return result

    def generate_denormalized(self, num_samples: int = 100) -> np.ndarray:
        """
        Generate and convert from [0, 1] → real-world units.

        Returns:
            np.ndarray of shape (num_samples, 7, 4) — Sleep hrs, Quality, HR bpm, Stress
        """
        raw = self.generate(num_samples)
        denorm = np.zeros_like(raw)

        for i, name in enumerate(SIGNAL_NAMES):
            r = DENORM_RANGES[name]
            denorm[:, :, i] = raw[:, :, i] * (r["max"] - r["min"]) + r["min"]

        return denorm

    def get_signal_names(self) -> list:
        """Return the ordered list of signal names."""
        return list(SIGNAL_NAMES)

    def is_loaded(self) -> bool:
        """Check if real weights are loaded."""
        return MODEL_PATH.exists()
