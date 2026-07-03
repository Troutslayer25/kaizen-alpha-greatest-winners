"""M-3 (representation tie-break de-bias) + M-7 (per-date deciles, per-fold AUC)."""
import numpy as np

from gws.phase_a1.clustering import _mean_within_group_var, _mean_within_group_var_multi
from gws.phase_a3.backtest import decile_lift


def test_multidim_scorer_credits_separation_on_nonmagnitude_dim():
    # Two groups IDENTICAL on dim 0 (magnitude) but cleanly separated on dim 1 (smoothness).
    # The old dim-0-only score sees no structure; the multi-dim score must reward the split.
    rng = np.random.default_rng(0)
    n = 120
    dim0 = rng.normal(0, 1, n)                          # no group info in magnitude
    dim1 = np.concatenate([rng.normal(-3, 0.2, n // 2), rng.normal(3, 0.2, n // 2)])
    X = np.column_stack([dim0, dim1])
    labels = np.array([0] * (n // 2) + [1] * (n // 2))

    dim0_only = _mean_within_group_var(dim0, labels) / dim0.var()   # ~1: no credit
    multidim = _mean_within_group_var_multi(X, labels)              # low: dim1 separation counted
    assert dim0_only > 0.8
    assert multidim < 0.6


def test_per_date_deciles_report_a_spread_ci():
    rng = np.random.default_rng(1)
    n_dates, per = 60, 40
    dates = np.repeat(np.arange(n_dates), per)
    scores = rng.normal(0, 1, n_dates * per)
    fwd = 0.02 * scores + rng.normal(0, 0.05, n_dates * per)   # real cross-sectional lift
    out = decile_lift(scores, fwd, dates=dates)
    assert out["spread"] > 0
    assert out["spread_ci"] is not None and out["spread_ci"][0] < out["spread"] < out["spread_ci"][1]


def test_pooled_decile_lift_still_works():
    rng = np.random.default_rng(2)
    scores = rng.normal(0, 1, 2000)
    fwd = 0.03 * scores + rng.normal(0, 0.05, 2000)
    out = decile_lift(scores, fwd)
    assert out["spread"] > 0 and out["spread_ci"] is None
