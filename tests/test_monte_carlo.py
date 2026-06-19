import numpy as np

from gws.phase_b2.monte_carlo import bootstrap_equity_paths, summarize_paths


def _returns(seed=0, n=500, mu=0.001, sigma=0.01):
    return np.random.default_rng(seed).normal(mu, sigma, n)


def test_positive_drift_paths_summary():
    eq = bootstrap_equity_paths(_returns(), n_paths=2000, horizon=252, seed=1)
    assert eq.shape == (2000, 252)
    s = summarize_paths(eq)
    assert s["terminal_median"] > 1.0
    assert s["cagr_median"] > 0.0
    lo, hi = s["cagr_ci"]
    assert lo < s["cagr_median"] < hi
    assert 0.0 < s["expected_max_drawdown"] < 1.0
    assert s["max_drawdown_95"] >= s["expected_max_drawdown"]


def test_deterministic_under_seed():
    r = _returns()
    s1 = summarize_paths(bootstrap_equity_paths(r, n_paths=1000, horizon=200, seed=7))
    s2 = summarize_paths(bootstrap_equity_paths(r, n_paths=1000, horizon=200, seed=7))
    assert s1 == s2


def test_block_bootstrap_shape():
    eq = bootstrap_equity_paths(_returns(), n_paths=500, horizon=252, block=10, seed=2)
    assert eq.shape == (500, 252)
    assert np.isfinite(eq).all()
