"""
Unit tests for lib.assesment.calibrator.

Design:
* All tests are pure-numpy — the predictor module imports tensorflow,
  so we never import predictor here. Calibrator is a standalone library
  precisely so it can be tested this way.
* We verify the *mathematical* invariants (temperature preserves argmax,
  identity is a no-op, ECE is zero for perfect calibration), not specific
  empirical numbers on a fixture cohort. Numeric sanity is spot-checked.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from lib.assesment.calibrator import (
    CLASSES,
    HEADS,
    CalibrationService,
    HeadCalibration,
    apply_isotonic,
    apply_temperature,
    brier_score,
    compute_metrics,
    default_service,
    expected_calibration_error,
    fit_isotonic_per_class,
    fit_temperature,
    load_calibration,
    save_calibration,
)


# ─── Temperature scaling ────────────────────────────────────────────────────

def test_temperature_identity_is_noop():
    probs = np.array([[0.1, 0.2, 0.7], [0.5, 0.3, 0.2]])
    out = apply_temperature(probs, 1.0)
    assert np.allclose(out, probs)


def test_temperature_preserves_argmax():
    """Core invariant of temperature scaling: argmax never changes."""
    rng = np.random.default_rng(42)
    # Build 50 random probability rows (3 classes).
    logits = rng.standard_normal((50, 3))
    probs = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
    for T in (0.5, 1.0, 2.0, 5.0, 10.0):
        out = apply_temperature(probs, T)
        assert (probs.argmax(1) == out.argmax(1)).all(), f"argmax broke at T={T}"


def test_temperature_softens_when_T_gt_1():
    """T > 1 should reduce the max probability (softening)."""
    probs = np.array([[0.05, 0.10, 0.85]])
    softened = apply_temperature(probs, 2.0)
    assert softened.max() < probs.max()


def test_temperature_sharpens_when_T_lt_1():
    """T < 1 should increase the max probability (sharpening)."""
    probs = np.array([[0.30, 0.30, 0.40]])
    sharpened = apply_temperature(probs, 0.5)
    assert sharpened.max() > probs.max()


def test_temperature_rows_sum_to_one():
    probs = np.array([[0.1, 0.3, 0.6], [0.33, 0.33, 0.34]])
    for T in (0.3, 1.0, 2.5):
        out = apply_temperature(probs, T)
        assert np.allclose(out.sum(axis=1), 1.0)


def test_temperature_rejects_non_positive():
    probs = np.array([[0.1, 0.3, 0.6]])
    with pytest.raises(ValueError):
        apply_temperature(probs, 0.0)
    with pytest.raises(ValueError):
        apply_temperature(probs, -1.0)


def test_fit_temperature_on_underconfident_data():
    """When predictions are *under*-confident the fitter should pick T < 1.

    Set up: label is class 2, but softmax says (0.30, 0.30, 0.40). Fitter
    should sharpen (T < 1) to push probability mass toward the correct
    class.
    """
    rng = np.random.default_rng(0)
    n = 500
    labels = rng.integers(0, 3, size=n)
    probs = np.full((n, 3), 0.30)
    probs[np.arange(n), labels] = 0.40  # under-confident but correct argmax
    T, nll = fit_temperature(probs, labels)
    assert T < 1.0, f"expected T<1 for under-confident correct preds, got {T}"


def test_fit_temperature_on_overconfident_wrong_data():
    """When predictions are over-confidently *wrong* the fitter should soften."""
    rng = np.random.default_rng(1)
    n = 500
    labels = rng.integers(0, 3, size=n)
    probs = np.full((n, 3), 0.02)
    # Place the high-confidence argmax on the wrong class 60% of the time.
    wrong = rng.random(n) < 0.6
    chosen = labels.copy()
    chosen[wrong] = (chosen[wrong] + 1) % 3
    probs[np.arange(n), chosen] = 0.96
    row_sums = probs.sum(axis=1, keepdims=True)
    probs = probs / row_sums  # renormalise just in case
    T, _ = fit_temperature(probs, labels)
    assert T > 1.0, f"expected T>1 for over-confident wrong preds, got {T}"


# ─── ECE / Brier ────────────────────────────────────────────────────────────

def test_ece_zero_for_perfect_predictions():
    """One-hot probabilities matching labels => ECE is 0."""
    labels = np.array([0, 1, 2, 1, 0])
    probs = np.eye(3)[labels]
    ece, bins = expected_calibration_error(probs, labels)
    assert ece == pytest.approx(0.0, abs=1e-9)


def test_ece_equals_gap_for_uniform_overconfidence():
    """If every prediction is correct with confidence 0.9, ECE = |1 - 0.9|."""
    n = 100
    labels = np.zeros(n, dtype=int)
    probs = np.zeros((n, 3))
    probs[:, 0] = 0.9
    probs[:, 1] = 0.05
    probs[:, 2] = 0.05
    ece, _ = expected_calibration_error(probs, labels)
    assert ece == pytest.approx(0.1, abs=1e-9)


def test_brier_zero_for_perfect_predictions():
    labels = np.array([0, 1, 2])
    probs = np.eye(3)[labels]
    assert brier_score(probs, labels) == pytest.approx(0.0, abs=1e-12)


def test_brier_bounded():
    """Brier on (N, 3) one-hots is in [0, 2]."""
    rng = np.random.default_rng(2)
    n = 100
    labels = rng.integers(0, 3, size=n)
    logits = rng.standard_normal((n, 3))
    probs = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
    b = brier_score(probs, labels)
    assert 0.0 <= b <= 2.0


def test_ece_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        expected_calibration_error(np.zeros((5, 3)), np.zeros(4, dtype=int))
    with pytest.raises(ValueError):
        expected_calibration_error(np.zeros(10), np.zeros(10, dtype=int))


def test_compute_metrics_roundtrip():
    rng = np.random.default_rng(3)
    n = 200
    labels = rng.integers(0, 3, size=n)
    logits = rng.standard_normal((n, 3))
    probs = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
    m = compute_metrics(probs, labels)
    d = m.to_dict()
    assert set(d.keys()) == {"ece", "brier", "accuracy", "n_samples", "reliability_bins"}
    assert d["n_samples"] == n
    assert len(d["reliability_bins"]) == 10


# ─── Isotonic regression ────────────────────────────────────────────────────

def test_isotonic_apply_preserves_row_sum():
    xs = [np.array([0.0, 0.5, 1.0]), np.array([0.0, 0.5, 1.0]),
          np.array([0.0, 0.5, 1.0])]
    ys = [np.array([0.0, 0.3, 1.0]), np.array([0.0, 0.4, 1.0]),
          np.array([0.0, 0.7, 1.0])]
    probs = np.array([[0.2, 0.3, 0.5], [0.6, 0.3, 0.1]])
    out = apply_isotonic(probs, xs, ys)
    assert np.allclose(out.sum(axis=1), 1.0)


def test_isotonic_fit_and_apply_reduces_ece():
    """Fit on over-confident synthetic data and check ECE drops."""
    rng = np.random.default_rng(7)
    n = 800
    labels = rng.integers(0, 3, size=n)

    # Over-confident correct-class probabilities (0.9 vs true prob 0.65).
    correct = rng.random(n) < 0.65
    probs = np.full((n, 3), 0.05)
    # When "correct" mask, put 0.9 on the label.
    chosen = np.where(correct, labels, (labels + rng.integers(1, 3, n)) % 3)
    probs[np.arange(n), chosen] = 0.9
    probs = probs / probs.sum(axis=1, keepdims=True)

    raw_ece, _ = expected_calibration_error(probs, labels)
    xs, ys = fit_isotonic_per_class(probs, labels)
    calibrated = apply_isotonic(probs, xs, ys)
    cal_ece, _ = expected_calibration_error(calibrated, labels)
    assert cal_ece <= raw_ece + 1e-6, (
        f"isotonic should not increase ECE: raw={raw_ece:.4f} cal={cal_ece:.4f}"
    )


# ─── HeadCalibration dataclass ──────────────────────────────────────────────

def test_head_calibration_identity_fields():
    hc = HeadCalibration.identity("stress")
    assert hc.head == "stress"
    assert hc.method == "identity"
    assert hc.temperature == 1.0


def test_head_calibration_to_dict_roundtrip():
    hc = HeadCalibration(head="anxiety", method="temperature", temperature=1.42)
    d = hc.to_dict()
    assert d["method"] == "temperature"
    assert d["temperature"] == 1.42


# ─── Persistence ────────────────────────────────────────────────────────────

def test_load_calibration_missing_file_returns_identity(tmp_path: Path):
    missing = tmp_path / "does_not_exist.json"
    heads = load_calibration(missing)
    assert set(heads.keys()) == set(HEADS)
    for h in HEADS:
        assert heads[h].method == "identity"


def test_save_and_load_roundtrip(tmp_path: Path):
    heads = {
        "stress": HeadCalibration(head="stress", method="temperature", temperature=1.7),
        "anxiety": HeadCalibration(
            head="anxiety", method="isotonic",
            isotonic_x=[[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]],
            isotonic_y=[[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]],
        ),
        "depression": HeadCalibration.identity("depression"),
    }
    path = tmp_path / "calibration.json"
    save_calibration(path, heads, fit_metadata={"n_samples": 123})

    loaded = load_calibration(path)
    assert loaded["stress"].method == "temperature"
    assert loaded["stress"].temperature == pytest.approx(1.7)
    assert loaded["anxiety"].method == "isotonic"
    assert loaded["anxiety"].isotonic_x is not None
    assert loaded["depression"].method == "identity"


def test_save_calibration_includes_fit_metadata(tmp_path: Path):
    heads = {h: HeadCalibration.identity(h) for h in HEADS}
    path = tmp_path / "cal.json"
    save_calibration(path, heads, fit_metadata={"cohort": "synthetic-v1"})
    payload = json.loads(path.read_text())
    assert payload["fit_metadata"]["cohort"] == "synthetic-v1"
    assert payload["schema_version"] == 1


# ─── CalibrationService ─────────────────────────────────────────────────────

def test_service_identity_when_no_file(tmp_path: Path):
    svc = CalibrationService(path=tmp_path / "nope.json")
    assert not svc.is_fitted()
    probs = np.array([0.1, 0.3, 0.6])
    out = svc.calibrate(probs, "stress")
    assert np.allclose(out, probs)


def test_service_applies_temperature_when_fitted(tmp_path: Path):
    heads = {
        "stress": HeadCalibration(head="stress", method="temperature", temperature=2.0),
        "anxiety": HeadCalibration.identity("anxiety"),
        "depression": HeadCalibration.identity("depression"),
    }
    path = tmp_path / "cal.json"
    save_calibration(path, heads)

    svc = CalibrationService(path=path)
    assert svc.is_fitted()

    # Temperature 2.0 should soften; identity on the other heads should not.
    raw = np.array([0.05, 0.10, 0.85])
    cal_stress = svc.calibrate(raw, "stress")
    cal_anx = svc.calibrate(raw, "anxiety")
    assert cal_stress.max() < raw.max()
    assert np.allclose(cal_anx, raw)


def test_service_status_shape(tmp_path: Path):
    heads = {h: HeadCalibration.identity(h) for h in HEADS}
    path = tmp_path / "cal.json"
    save_calibration(path, heads, fit_metadata={"source": "unit-test"})
    svc = CalibrationService(path=path)
    st = svc.status()
    assert set(st.keys()) == {"calibration_path", "file_exists", "is_fitted",
                              "fit_metadata", "heads"}
    assert st["file_exists"] is True
    assert st["is_fitted"] is False
    assert st["fit_metadata"] == {"source": "unit-test"}
    assert set(st["heads"].keys()) == set(HEADS)


def test_service_accepts_both_1d_and_2d(tmp_path: Path):
    svc = CalibrationService(path=tmp_path / "absent.json")
    one_d = svc.calibrate(np.array([0.2, 0.3, 0.5]), "stress")
    assert one_d.ndim == 1 and one_d.shape == (3,)
    two_d = svc.calibrate(np.array([[0.2, 0.3, 0.5], [0.6, 0.3, 0.1]]), "stress")
    assert two_d.ndim == 2 and two_d.shape == (2, 3)


def test_default_service_is_singleton():
    svc1 = default_service()
    svc2 = default_service()
    assert svc1 is svc2


# ─── Module-level constants ─────────────────────────────────────────────────

def test_heads_and_classes_match_predictor_contract():
    assert HEADS == ("stress", "anxiety", "depression")
    assert CLASSES == ("low", "moderate", "high")
