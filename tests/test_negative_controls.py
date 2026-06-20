import numpy as np

from gws.common.negative_controls import (
    shuffle_labels, permute_features_within_date, shift_labels_by,
    negative_control_report, passes_negative_controls,
)
from gws.phase_a3.ml_bakeoff import build_estimators, run_walk_forward


def _world(seed=0, n_dates=150, per_date=10):
    # A proper cross-sectional panel: many tickers per date, so permute-within-date is a
    # real control (matches the study, where each date has thousands of names).
    rng = np.random.default_rng(seed)
    n = n_dates * per_date
    t = np.repeat(np.arange(n_dates), per_date)
    signal = rng.normal(0, 1, n)
    y = (signal + rng.normal(0, 0.5, n) > 0).astype(int)
    X = np.column_stack([signal, rng.normal(0, 1, n)])
    return X, y, t


def _auc_fn(X, y, t):
    res = run_walk_forward(X, y, t, [90, 112, 135], label_horizon=3,
                           build_estimator=build_estimators()["random_forest"])
    return res["auc"]


def test_shuffle_labels_is_a_permutation():
    y = np.array([0, 0, 1, 1, 1])
    s = shuffle_labels(y, seed=1)
    assert sorted(s) == sorted(y) and len(s) == len(y)


def test_permute_within_date_preserves_daily_distribution():
    X = np.arange(12, dtype=float).reshape(6, 2)
    dates = np.array([1, 1, 1, 2, 2, 2])
    out = permute_features_within_date(X, dates, seed=0)
    # each date's set of rows is preserved, only order changes
    for d in (1, 2):
        a = X[dates == d]; b = out[dates == d]
        assert sorted(a.sum(1)) == sorted(b.sum(1))


def test_shift_labels_misaligns():
    y = np.arange(10)
    assert not np.array_equal(shift_labels_by(y, 3), y)


def test_negative_controls_pass_on_clean_pipeline():
    # Real signal recovers; every corruption collapses to ~chance.
    X, y, t = _world(0)
    report = negative_control_report(X, y, t, _auc_fn, seed=0)
    assert report["real"] > 0.65
    for k in ("shuffled_labels", "permuted_features", "shifted_labels"):
        assert abs(report[k] - 0.5) < 0.1, f"{k} should be ~chance, got {report[k]}"
    assert passes_negative_controls(report, margin=0.1)


def test_leaky_evaluation_fails_negative_controls():
    # A BROKEN evaluation (fit and score on the same rows — no holdout) memorizes even random
    # labels, so it scores high under shuffled labels. The harness must catch that: this is
    # exactly the CV-integrity failure the shuffle-labels control exists to detect.
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score

    def _leaky_in_sample_auc(X, y, t):
        m = RandomForestClassifier(n_estimators=60, random_state=0).fit(X, y)
        return roc_auc_score(y, m.predict_proba(X)[:, 1])

    X, y, t = _world(2)
    report = negative_control_report(X, y, t, _leaky_in_sample_auc, seed=0)
    assert report["shuffled_labels"] > 0.6      # memorized random labels -> not chance
    assert not passes_negative_controls(report, margin=0.1)
