"""
Unit tests for ``lib.activity.cbt_calibrator``.

Covers:
* Identity passthrough — zero-impact when no JSON is present.
* Temperature round-trip — T > 1 softens, T < 1 sharpens, argmax stable.
* Isotonic round-trip — per-class mapping + row renormalisation.
* Dict API — classes preserved, unknown keys pass through.
* JSON persistence — save/load is lossless for metrics + parameters.
* Reorder — probs passed in shuffled class order come back in the same order.
* Singleton behaviour — reload flag produces a fresh service.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from lib.CBT.cbt_calibrator import (
    CBTCalibration,
    CbtCalibrationService,
    CLASS_ORDER,
    NUM_CLASSES,
    _reorder_to_canonical,
    default_service,
    load_cbt_calibration,
    prob_dict_to_vector,
    reset_default_service,
    save_cbt_calibration,
    vector_to_prob_dict,
)
from lib.assesment.calibrator import (
    CalibrationMetrics,
    ReliabilityBin,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def _make_simplex(peak_idx: int, peak_mass: float = 0.6) -> np.ndarray:
    """Build a length-11 simplex with ``peak_mass`` on ``peak_idx`` and
    the remainder uniformly spread over the other classes."""
    v = np.full(NUM_CLASSES, (1.0 - peak_mass) / (NUM_CLASSES - 1))
    v[peak_idx] = peak_mass
    assert abs(v.sum() - 1.0) < 1e-9
    return v


@pytest.fixture
def simplex():
    return _make_simplex(peak_idx=1, peak_mass=0.55)


@pytest.fixture
def temperature_service():
    return CbtCalibrationService(
        CBTCalibration(method="temperature", temperature=2.0)
    )


@pytest.fixture
def identity_service():
    return CbtCalibrationService(CBTCalibration.identity())


# ── CLASS_ORDER shape ─────────────────────────────────────────────────────────

class TestClassOrder:
    def test_eleven_classes(self):
        assert NUM_CLASSES == 11
        assert len(CLASS_ORDER) == 11

    def test_no_duplicates(self):
        assert len(set(CLASS_ORDER)) == 11

    def test_none_is_first(self):
        assert CLASS_ORDER[0] == "none"

    def test_distortions_present(self):
        assert "catastrophizing" in CLASS_ORDER
        assert "mind_reading" in CLASS_ORDER


# ── Identity passthrough ──────────────────────────────────────────────────────

class TestIdentity:
    def test_identity_preserves_input(self, identity_service, simplex):
        out = identity_service.calibrate(simplex)
        assert np.allclose(out, simplex, atol=1e-9)

    def test_identity_is_not_fitted(self, identity_service):
        assert identity_service.is_fitted is False
        assert identity_service.method == "identity"

    def test_identity_status_ece_improvement_none(self, identity_service):
        s = identity_service.status()
        assert s["ece_improvement"] is None
        assert s["is_fitted"] is False

    def test_missing_file_falls_back_to_identity(self, tmp_path):
        svc = CbtCalibrationService.from_path(tmp_path / "absent.json")
        assert svc.method == "identity"
        assert svc.is_fitted is False


# ── Temperature scaling ───────────────────────────────────────────────────────

class TestTemperature:
    def test_T_gt_1_softens(self, simplex):
        svc = CbtCalibrationService(
            CBTCalibration(method="temperature", temperature=2.0)
        )
        out = svc.calibrate(simplex)
        assert out.max() < simplex.max()
        assert np.isclose(out.sum(), 1.0)

    def test_T_lt_1_sharpens(self, simplex):
        svc = CbtCalibrationService(
            CBTCalibration(method="temperature", temperature=0.5)
        )
        out = svc.calibrate(simplex)
        assert out.max() > simplex.max()
        assert np.isclose(out.sum(), 1.0)

    def test_T_1_is_noop(self, simplex):
        svc = CbtCalibrationService(
            CBTCalibration(method="temperature", temperature=1.0)
        )
        out = svc.calibrate(simplex)
        assert np.allclose(out, simplex, atol=1e-9)

    def test_argmax_preserved(self, simplex):
        svc = CbtCalibrationService(
            CBTCalibration(method="temperature", temperature=3.0)
        )
        out = svc.calibrate(simplex)
        assert simplex.argmax() == out.argmax()

    def test_batch_shape_preserved(self, temperature_service, simplex):
        batch = np.stack([simplex, _make_simplex(3), _make_simplex(7)])
        out = temperature_service.calibrate(batch)
        assert out.shape == batch.shape
        assert np.allclose(out.sum(axis=1), 1.0)


# ── Isotonic ──────────────────────────────────────────────────────────────────

class TestIsotonic:
    def _make_isotonic_service(self):
        # Simple monotonic mapping: raw=[0,0.5,1] -> cal=[0,0.3,1].
        # That's a flat region in the middle so a 0.5 raw prob maps to 0.3.
        xs = [[0.0, 0.5, 1.0]] * NUM_CLASSES
        ys = [[0.0, 0.3, 1.0]] * NUM_CLASSES
        return CbtCalibrationService(
            CBTCalibration(method="isotonic", isotonic_x=xs, isotonic_y=ys)
        )

    def test_isotonic_applies_and_renormalises(self, simplex):
        svc = self._make_isotonic_service()
        out = svc.calibrate(simplex)
        assert np.isclose(out.sum(), 1.0)

    def test_isotonic_missing_params_falls_back(self, simplex):
        svc = CbtCalibrationService(
            CBTCalibration(method="isotonic", isotonic_x=None, isotonic_y=None)
        )
        out = svc.calibrate(simplex)
        # Pass-through (no-op renormalise) means the relative order
        # should match the input.
        assert out.argmax() == simplex.argmax()


# ── Dict API ──────────────────────────────────────────────────────────────────

class TestDictApi:
    def test_dict_round_trip_sums_to_one(self, temperature_service):
        d = {"none": 0.5, "catastrophizing": 0.3, "mind_reading": 0.2}
        out = temperature_service.calibrate_prob_dict(d)
        assert abs(sum(out.values()) - 1.0) < 1e-6
        assert len(out) == NUM_CLASSES

    def test_dict_includes_all_canonical_classes(self, temperature_service):
        d = {"none": 1.0}
        out = temperature_service.calibrate_prob_dict(d)
        for c in CLASS_ORDER:
            assert c in out

    def test_unknown_keys_preserved(self, temperature_service):
        d = {"none": 0.5, "catastrophizing": 0.5, "my_custom_key": 99.0}
        out = temperature_service.calibrate_prob_dict(d)
        assert out["my_custom_key"] == 99.0

    def test_calibrate_rejects_dict_input(self, temperature_service):
        with pytest.raises(TypeError, match="calibrate_prob_dict"):
            temperature_service.calibrate({"none": 1.0})


# ── Vector helpers ────────────────────────────────────────────────────────────

class TestVectorHelpers:
    def test_prob_dict_to_vector_missing_zero(self):
        v = prob_dict_to_vector({"none": 0.7, "catastrophizing": 0.3})
        assert v.shape == (NUM_CLASSES,)
        assert v[0] == 0.7
        # Classes not in dict become zero.
        assert v[CLASS_ORDER.index("mind_reading")] == 0.0

    def test_vector_to_prob_dict_keys(self):
        v = np.zeros(NUM_CLASSES)
        v[0] = 1.0
        d = vector_to_prob_dict(v)
        assert d["none"] == 1.0
        assert set(d.keys()) == set(CLASS_ORDER)

    def test_reorder_to_canonical(self):
        # Alphabetical source order (what sklearn LabelEncoder produces)
        source = tuple(sorted(CLASS_ORDER))
        # Build a one-hot with 1.0 on "none" in the source order.
        n_idx = source.index("none")
        src = np.zeros((1, NUM_CLASSES))
        src[0, n_idx] = 1.0
        out = _reorder_to_canonical(src, source, CLASS_ORDER)
        # After reordering, "none" should land at CLASS_ORDER[0].
        assert out[0, 0] == 1.0
        assert out.sum() == 1.0


# ── JSON persistence ──────────────────────────────────────────────────────────

class TestPersistence:
    def test_save_load_roundtrip_temperature(self, tmp_path):
        cal = CBTCalibration(
            method="temperature",
            temperature=1.7,
            fit_date="2026-04-24T12:00:00+00:00",
            n_calibration_samples=123,
        )
        p = tmp_path / "cbt_calibration.json"
        save_cbt_calibration(p, cal, fit_metadata={"note": "test"})
        loaded = load_cbt_calibration(p)
        assert loaded.method == "temperature"
        assert loaded.temperature == 1.7
        assert loaded.n_calibration_samples == 123
        assert loaded.fit_date == "2026-04-24T12:00:00+00:00"

    def test_save_load_roundtrip_isotonic(self, tmp_path):
        xs = [[0.0, 0.5, 1.0]] * NUM_CLASSES
        ys = [[0.0, 0.4, 1.0]] * NUM_CLASSES
        cal = CBTCalibration(method="isotonic", isotonic_x=xs, isotonic_y=ys)
        p = tmp_path / "cbt_calibration.json"
        save_cbt_calibration(p, cal)
        loaded = load_cbt_calibration(p)
        assert loaded.method == "isotonic"
        assert loaded.isotonic_x == xs
        assert loaded.isotonic_y == ys

    def test_save_load_roundtrip_metrics(self, tmp_path):
        raw = CalibrationMetrics(
            ece=0.05, brier=0.02, accuracy=0.9, n_samples=200,
            reliability_bins=[
                ReliabilityBin(0.0, 0.5, 80, 0.3, 0.32),
                ReliabilityBin(0.5, 1.0, 120, 0.8, 0.78),
            ],
        )
        cal = CBTCalibration(
            method="temperature", temperature=1.4,
            raw_metrics=raw, calibrated_metrics=raw,
        )
        p = tmp_path / "c.json"
        save_cbt_calibration(p, cal)
        loaded = load_cbt_calibration(p)
        assert loaded.raw_metrics is not None
        assert loaded.raw_metrics.ece == 0.05
        assert len(loaded.raw_metrics.reliability_bins) == 2
        assert loaded.raw_metrics.reliability_bins[0].n_samples == 80

    def test_load_missing_file_returns_identity(self, tmp_path):
        loaded = load_cbt_calibration(tmp_path / "nonexistent.json")
        assert loaded.method == "identity"

    def test_envelope_schema_version(self, tmp_path):
        cal = CBTCalibration.identity()
        p = tmp_path / "c.json"
        save_cbt_calibration(p, cal, fit_metadata={"rng": 42})
        with open(p) as f:
            payload = json.load(f)
        assert payload["schema_version"] == 1
        assert payload["component"] == "component4.cbt"
        assert payload["fit_metadata"]["rng"] == 42


# ── Status payload ────────────────────────────────────────────────────────────

class TestStatus:
    def test_status_payload_shape(self, tmp_path):
        cal = CBTCalibration(
            method="temperature",
            temperature=1.5,
            n_calibration_samples=200,
            raw_metrics=CalibrationMetrics(
                ece=0.05, brier=0.02, accuracy=0.9, n_samples=200,
            ),
            calibrated_metrics=CalibrationMetrics(
                ece=0.01, brier=0.015, accuracy=0.9, n_samples=200,
            ),
        )
        p = tmp_path / "c.json"
        save_cbt_calibration(p, cal)
        svc = CbtCalibrationService.from_path(p)
        s = svc.status()
        required = {
            "loaded", "path", "is_fitted", "method", "temperature",
            "n_classes", "class_names", "n_calibration_samples",
            "fit_date", "raw_metrics", "calibrated_metrics",
            "ece_improvement",
        }
        assert required <= set(s.keys())
        assert s["is_fitted"] is True
        assert s["method"] == "temperature"
        # ece_improvement = (0.05 - 0.01) / 0.05 = 0.8
        assert s["ece_improvement"] == 0.8

    def test_status_no_metrics_no_improvement(self):
        svc = CbtCalibrationService(
            CBTCalibration(method="temperature", temperature=1.5)
        )
        s = svc.status()
        assert s["ece_improvement"] is None


# ── Column permutation ────────────────────────────────────────────────────────

class TestClassOrderPermutation:
    def test_shuffled_input_returns_in_shuffled_order(self, temperature_service, simplex):
        shuffled = tuple(sorted(CLASS_ORDER))
        idx = {n: i for i, n in enumerate(CLASS_ORDER)}
        src = np.array([simplex[idx[n]] for n in shuffled])
        out = temperature_service.calibrate(src, class_order=shuffled)
        assert abs(out.sum() - 1.0) < 1e-6
        # The max class name should match between input and output — a
        # valid sanity check on the permute-in/permute-out round-trip.
        assert shuffled[out.argmax()] == shuffled[src.argmax()]


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestSingleton:
    def test_default_service_returns_same_instance(self, tmp_path):
        # Point at a missing path so we get identity without touching
        # the real ml_models directory.
        p = tmp_path / "no_cal.json"
        reset_default_service()
        s1 = default_service(path=p)
        s2 = default_service(path=p)
        assert s1 is s2

    def test_reload_flag_produces_fresh_instance(self, tmp_path):
        p = tmp_path / "no_cal.json"
        reset_default_service()
        s1 = default_service(path=p)
        s2 = default_service(path=p, reload=True)
        assert s1 is not s2

    def test_reset_clears_cache(self, tmp_path):
        p = tmp_path / "no_cal.json"
        reset_default_service()
        s1 = default_service(path=p)
        reset_default_service()
        s2 = default_service(path=p)
        assert s1 is not s2


# ── Invalid input ─────────────────────────────────────────────────────────────

class TestInvalidInput:
    def test_3d_input_raises(self, temperature_service):
        with pytest.raises(ValueError, match="1-D or 2-D"):
            temperature_service.calibrate(np.zeros((2, 3, NUM_CLASSES)))

    def test_identity_service_from_identity_factory(self):
        cal = CBTCalibration.identity()
        assert cal.method == "identity"
        assert cal.temperature == 1.0
