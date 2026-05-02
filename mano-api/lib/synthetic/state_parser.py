"""
Canonical patient-state <-> tensor helpers.

Previously each router module hand-rolled its own ``parse_patient_state`` and
``clamp_simulated_vitals``. That drift is a maintenance trap: if feature order
or clamp ranges ever change (they shouldn't — the models are frozen), a
subtle divergence between routers would silently corrupt inferences.

This module is the SINGLE source of truth for:

* converting a ``PatientState`` Pydantic payload into the dynamic + static
  numpy arrays expected by the frozen Seq2Seq / Hybrid-LSTM / PPO models, and
* clamping raw Seq2Seq outputs back into schema-valid ``DayVitals``.

Feature ordering mirrors the exact order used during model training — any
deviation from this order WILL silently corrupt predictions while still
producing "valid" responses, which is the worst class of bug.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from schemas.synthetic.simulation_schema import DayVitals, PatientState


# ── Feature-order canonicals ───────────────────────────────────────────────
#
# Documented here so downstream reviewers can audit without reading model
# checkpoints. Changing these without retraining the frozen models is a
# correctness bug — they are effectively immutable.
DYNAMIC_FEATURE_ORDER: Tuple[str, ...] = (
    "sleep_hours",
    "sleep_quality",
    "heart_rate",
    "stress_level",
)

# Clamp ranges match schemas.synthetic.simulation_schema.DayVitals constraints.
_CLAMP_RANGES = {
    "sleep_hours": (0.0, 24.0),
    "sleep_quality": (0.0, 1.0),
    "heart_rate": (40.0, 200.0),
    "stress_level": (0.0, 1.0),
}


def parse_patient_state(state: PatientState) -> Tuple[np.ndarray, np.ndarray]:
    """Convert a validated ``PatientState`` payload into inference tensors.

    Returns a ``(dynamic_np, static_np)`` tuple with shapes::

        dynamic_np: (1, T, 4)   — T days × 4 features (sleep, quality, hr, stress)
        static_np:  (1, 30)     — demographic / historical feature vector

    The leading ``1`` is the batch dimension; we always infer one patient at a
    time at the route layer (batch APIs sit on top of this).
    """
    static_np = np.array([state.static_data.features], dtype=np.float32)

    dyn_rows: List[List[float]] = []
    for day in state.dynamic_history:
        dyn_rows.append([
            float(day.sleep_hours),
            float(day.sleep_quality),
            float(day.heart_rate),
            float(day.stress_level),
        ])

    dynamic_np = np.array([dyn_rows], dtype=np.float32)
    return dynamic_np, static_np


def clamp_simulated_vitals(future_dyn_np: np.ndarray) -> List[DayVitals]:
    """Project raw Seq2Seq output into schema-valid ``DayVitals`` objects.

    The Seq2Seq simulator works in a normalised latent space and can produce
    values that overshoot physically-valid ranges (e.g. sleep_quality=1.03).
    We clamp to the schema ranges rather than silently rejecting the sample —
    the clamp bias is tiny (< 2% in practice) and preserves UX smoothness.
    """
    vitals: List[DayVitals] = []
    for day_idx in range(future_dyn_np.shape[1]):
        row = future_dyn_np[0, day_idx]
        vitals.append(DayVitals(
            sleep_hours=float(np.clip(row[0], *_CLAMP_RANGES["sleep_hours"])),
            sleep_quality=float(np.clip(row[1], *_CLAMP_RANGES["sleep_quality"])),
            heart_rate=float(np.clip(row[2], *_CLAMP_RANGES["heart_rate"])),
            stress_level=float(np.clip(row[3], *_CLAMP_RANGES["stress_level"])),
        ))
    return vitals


def vitals_to_matrix(vitals: List[DayVitals]) -> np.ndarray:
    """Inverse of ``clamp_simulated_vitals`` — list of DayVitals → (1, T, 4)."""
    rows = [[v.sleep_hours, v.sleep_quality, v.heart_rate, v.stress_level] for v in vitals]
    return np.array([rows], dtype=np.float32)
