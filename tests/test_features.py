import numpy as np

from gws.phase_a2.features_price_volume import compute_features
from gws.common.pit_audit import assert_future_invariant


def _series(n=400, seed=0):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.cumprod(1 + rng.normal(0.0003, 0.01, n))
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    bench = 100.0 * np.cumprod(1 + rng.normal(0.0002, 0.008, n))
    return close, high, low, volume, bench


def test_features_are_future_invariant():
    # The core PIT guarantee: no feature at index i may depend on any bar after i.
    close, high, low, volume, bench = _series(seed=1)
    for i in (260, 300, 380):
        feats = assert_future_invariant(
            compute_features,
            {"close": close, "high": high, "low": low, "volume": volume, "bench_close": bench},
            i,
        )
        assert "atr_pct_21" in feats and "rel_strength_63" in feats


def test_contraction_lowers_atr_pct():
    volatile = 100.0 + 2.0 * ((-1.0) ** np.arange(120))   # alternating +/-2
    tight = 100.0 + 0.2 * ((-1.0) ** np.arange(120))      # alternating +/-0.2
    close = np.concatenate([volatile, tight])
    high, low = close + 0.1, close - 0.1
    volume = np.full(len(close), 2_000_000.0)
    f_vol = compute_features(close, high, low, volume, 110)
    f_tight = compute_features(close, high, low, volume, 230)
    assert f_tight["atr_pct_21"] < f_vol["atr_pct_21"]


def test_dist_from_high_zero_at_new_high():
    close = np.linspace(100.0, 150.0, 260)               # strictly increasing
    high, low = close * 1.001, close * 0.999
    volume = np.full(len(close), 1e6)
    f = compute_features(close, high, low, volume, 259)
    assert abs(f["dist_from_high_63"]) < 1e-9            # current bar is the window high


def test_relative_strength_sign():
    n = 200
    close = 100.0 * (1.20) ** (np.arange(n) / n)         # stock +20% over the window
    bench = 100.0 * (1.10) ** (np.arange(n) / n)         # benchmark +10%
    high, low = close * 1.001, close * 0.999
    volume = np.full(n, 1e6)
    f = compute_features(close, high, low, volume, n - 1, bench_close=bench)
    assert f["rel_strength_126"] > 0                     # outperformance


def test_skips_unavailable_lookbacks():
    close, high, low, volume, _ = _series(n=40, seed=2)
    f = compute_features(close, high, low, volume, 30)
    assert "atr_pct_21" in f
    assert "atr_pct_63" not in f                         # 63-day window not available at i=30
    assert "dist_from_high_126" not in f
