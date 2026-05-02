"""
CTGAN Inference Service

Loads the trained CTGAN model (pickle) and exposes component1 tabular
patient profile generation at the backend service layer.

The model was trained on the Mental Health in Tech Survey dataset
(19 categorical + 1 numerical feature = 172 encoded dimensions).

Output: pandas DataFrame with the original column schema.

Usage:
  service = CTGANService()
  df = service.generate(num_samples=50)   # DataFrame with 20 columns
  columns = service.get_columns()         # list of column names
"""
import pickle
import traceback
import pandas as pd
import numpy as np
from pathlib import Path

from core.logging import get_logger

logger = get_logger("ctgan_service")

MODEL_PATH = Path(__file__).parent.parent.parent / "ml_models" / "component1" / "ctgan_model_MENTAL_HEALTH_TECH.pkl"

# The original schema columns from training config
CATEGORICAL_FEATURES = [
    "Gender", "Country", "self_employed", "family_history", "treatment",
    "work_interfere", "no_employees", "remote_work", "tech_company",
    "benefits", "care_options", "wellness_program", "seek_help",
    "anonymity", "leave", "mental_health_consequence",
    "phys_health_consequence", "coworkers", "supervisor",
]
NUMERICAL_FEATURES = ["Age"]
ALL_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES


class CTGANService:
    """Wraps the CTGAN model for inference (component1 tabular data generation)."""

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

        self.model = None

        if MODEL_PATH.exists():
            try:
                # Ensure ctgan is importable before pickle tries to deserialize.
                # Uvicorn's --reload subprocess on Windows can lose venv site-packages.
                try:
                    import ctgan  # noqa: F401
                except ImportError:
                    import site, sys
                    venv_sp = Path(__file__).resolve().parent.parent.parent / "venv" / "Lib" / "site-packages"
                    if venv_sp.exists() and str(venv_sp) not in sys.path:
                        sys.path.insert(0, str(venv_sp))
                        import ctgan  # noqa: F401

                with open(MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                logger.info("ctgan_loaded", path=str(MODEL_PATH))
            except Exception as e:
                logger.error("ctgan_load_failed", error=str(e))
                traceback.print_exc()
        else:
            logger.warning(
                "ctgan_not_found",
                path=str(MODEL_PATH),
                msg="CTGAN model not available — generation will fail",
            )

        self._initialized = True

    # ────────────────────────────────────────────────

    def generate(self, num_samples: int = 100) -> pd.DataFrame:
        """
        Generate component1 patient profiles.

        Returns:
            pd.DataFrame with columns matching the original training schema.
        """
        if self.model is None:
            raise RuntimeError("CTGAN model not loaded — cannot generate samples.")

        synthetic_df = self.model.sample(num_samples)

        # Post-processing: clamp Age to reasonable range
        if "Age" in synthetic_df.columns:
            synthetic_df["Age"] = synthetic_df["Age"].clip(18, 80).astype(int)

        logger.info("ctgan_generated", num_samples=num_samples, columns=len(synthetic_df.columns))
        return synthetic_df

    def generate_as_dict(self, num_samples: int = 100) -> list:
        """
        Generate and return as list of dicts (JSON-serializable).
        """
        df = self.generate(num_samples)
        return df.to_dict(orient="records")

    def get_columns(self) -> list:
        """Return the expected output column names."""
        return ALL_FEATURES

    def get_categorical_features(self) -> list:
        """Return categorical feature names."""
        return CATEGORICAL_FEATURES

    def get_numerical_features(self) -> list:
        """Return numerical feature names."""
        return NUMERICAL_FEATURES

    def is_loaded(self) -> bool:
        """Check if model is available."""
        return self.model is not None
