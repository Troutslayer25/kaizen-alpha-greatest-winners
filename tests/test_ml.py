import numpy as np
import pytest

from gws.phase_a3.ml_bakeoff import (
    build_estimators, run_walk_forward, permutation_importance_oos,
)
from gws.phase_a3.calibration import (
    fit_calibrator, reliability_table, brier, calibration_decay,
)


def _classification_world(seed=0, n=1500):
    rng = np.random.default_rng(seed)
    t = np.sort(rng.integers(0, 1000, n))
    signal = rng.normal(0, 1, n)
    null = rng.normal(0, 1, n)
    y = (signal + rng.normal(0, 0.5, n) > 0).astype(int)
    return t, signal, null, y


BOUNDS = [600, 750, 900]
K = 5


def test_model_recovers_signal():
    t, signal, null, y = _classification_world(0)
    X = np.column_stack([signal, null])
    res = run_walk_forward(X, y, t, BOUNDS, K, build_estimators()["random_forest"])
    assert res["auc"] > 0.75
    assert 0.0 <= res["brier"] <= 0.25


def test_model_finds_no_signal_in_noise():
    t, signal, null, y = _classification_world(1)
    rng = np.random.default_rng(99)
    X = np.column_stack([null, rng.normal(0, 1, len(y))])   # both columns independent of y
    res = run_walk_forward(X, y, t, BOUNDS, K, build_estimators()["random_forest"])
    assert res["auc"] < 0.60                                 # ~chance


def test_permutation_importance_ranks_signal_over_null():
    t, signal, null, y = _classification_world(2)
    X = np.column_stack([signal, null])
    rf = build_estimators()["random_forest"]()
    rf.fit(X, y)
    imp = permutation_importance_oos(rf, X, y, n_repeats=5)
    assert imp[0] > imp[1]                                   # signal column dominates


@pytest.mark.parametrize("name", ["xgboost", "lightgbm", "elastic_net_logistic"])
def test_estimators_run(name):
    t, signal, null, y = _classification_world(3)
    X = np.column_stack([signal, null])
    res = run_walk_forward(X, y, t, BOUNDS, K, build_estimators()[name])
    assert res["auc"] > 0.7                                  # all real learners recover the signal


def test_isotonic_calibration_improves_brier():
    rng = np.random.default_rng(4)
    n = 4000
    latent = rng.normal(0, 1, n)
    p_true = 1 / (1 + np.exp(-latent))
    y = (rng.uniform(size=n) < p_true).astype(int)
    p_overconf = np.clip((p_true - 0.5) * 2.0 + 0.5, 0, 1)   # miscalibrated (over-confident)

    half = n // 2
    cal = fit_calibrator(p_overconf[:half], y[:half], method="isotonic")
    before = brier(p_overconf[half:], y[half:])
    after = brier(cal(p_overconf[half:]), y[half:])
    assert after <= before                                    # calibration does not worsen Brier
    assert len(reliability_table(p_overconf, y)) > 0


def test_calibration_decay_no_alarm_when_discrimination_strong():
    # Strongly discriminating, already well-calibrated probs: the transform does little
    # heavy lifting -> no alarm.
    rng = np.random.default_rng(8)
    n = 4000
    p_true = 1 / (1 + np.exp(-rng.normal(0, 2, n)))           # well-separated
    y = (rng.uniform(size=n) < p_true).astype(int)
    d = calibration_decay(p_true, p_true, y)
    assert d["auc"] > 0.8
    assert not d["alarm"]


def test_calibration_decay_alarms_when_transform_does_the_work():
    # Near-random ranking (AUC ~0.5) but the calibration transform pulls Brier toward the
    # base rate -> the transform is masking thin discrimination -> alarm.
    rng = np.random.default_rng(9)
    n = 4000
    y = rng.integers(0, 2, n)
    raw = np.clip(0.5 + rng.normal(0, 0.25, n), 0.01, 0.99)   # uninformative, noisy
    cal = fit_calibrator(raw[: n // 2], y[: n // 2], method="isotonic")
    calibrated = cal(raw)
    d = calibration_decay(raw, calibrated, y)
    assert d["auc"] < 0.6
    assert d["alarm"]
