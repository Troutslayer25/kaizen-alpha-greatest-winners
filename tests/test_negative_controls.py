import numpy as np

from gws.common.negative_controls import (
    shuffle_labels, permute_features_within_date, shift_labels_within_ticker,
    negative_control_report, negative_control_verdicts,
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
    tickers = np.tile(np.arange(per_date), n_dates)
    return X, y, t, tickers


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
    for d in (1, 2):
        a = X[dates == d]; b = out[dates == d]
        assert sorted(a.sum(1)) == sorted(b.sum(1))


def test_within_ticker_shift_stays_inside_each_ticker():
    y = np.array([0, 1, 2, 3, 10, 11, 12, 13])
    tk = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    out = shift_labels_within_ticker(y, tk, k=1)
    # every value stays with its own ticker's label pool
    assert set(out[tk == 0]) == {0, 1, 2, 3}
    assert set(out[tk == 1]) == {10, 11, 12, 13}
    assert not np.array_equal(out, y)


def test_clean_pipeline_is_leak_free_and_has_signal():
    X, y, t, tk = _world(0)
    report = negative_control_report(X, y, t, _auc_fn, tickers=tk, seed=0, n_null=8)
    v = negative_control_verdicts(report)
    assert report["real"] > 0.65
    assert report["shuffle_null"]["mean"] < 0.6          # learned chance band sits near 0.5
    assert v["leak_free"] and v["has_signal"] and v["passes"]


def test_leaky_evaluation_is_flagged_not_leak_free():
    # A BROKEN evaluation (fit and score on the same rows) memorizes even random labels, so its
    # shuffle-null band is elevated far above chance -> not leak_free -> does not pass.
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score

    def _leaky_in_sample_auc(X, y, t):
        m = RandomForestClassifier(n_estimators=60, random_state=0).fit(X, y)
        return roc_auc_score(y, m.predict_proba(X)[:, 1])

    X, y, t, tk = _world(2)
    report = negative_control_report(X, y, t, _leaky_in_sample_auc, tickers=tk, seed=0, n_null=8)
    v = negative_control_verdicts(report)
    assert report["shuffle_null"]["mean"] > 0.6          # memorized random labels
    assert not v["leak_free"]
    assert not v["passes"]
