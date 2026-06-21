import numpy as np
import pandas as pd

from gws.phase_a2.features_price_volume import compute_features
from gws.phase_a2.group_strength import group_strength_features
from gws.phase_a2.feature_catalog import catalog_rows, MOTIVATIONS
from gws.common.resample import resample_weekly
from gws.common.pit_audit import assert_future_invariant


def _series(n=400, seed=0):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.cumprod(1 + rng.normal(0.0003, 0.01, n))
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    return close, high, low, volume


# ---- #3 contraction / base structure ----

def test_base_and_contraction_features_present_and_sane():
    close, high, low, volume = _series()
    f = compute_features(close, high, low, volume, 380)
    assert 0.0 <= f["range_position_63"] <= 1.0
    assert f["base_depth_63"] >= 0.0
    assert "vol_contraction_63" in f and "tight_days_share_63" in f


def test_vol_contraction_detects_tightening():
    # High-vol early, low-vol late, transition placed at the window midpoint so the recent
    # half is calm and the earlier half is wild -> contraction ratio < 1. (i=312, lb=126 ->
    # recent half days 250-312 [calm], earlier half days 187-249 [wild].)
    early = 100 + 3.0 * ((-1.0) ** np.arange(250))
    late = 100 + 0.3 * ((-1.0) ** np.arange(150))
    close = np.concatenate([early, late])
    high, low = close + 0.2, close - 0.2
    vol = np.full(len(close), 1e6)
    f = compute_features(close, high, low, vol, 312, lookbacks=(126,))
    assert f["vol_contraction_126"] < 1.0


# ---- #4 RS line ----

def test_rs_line_at_high_when_outperforming():
    n = 200
    stock = 100 * (1.30) ** (np.arange(n) / n)     # +30%
    bench = 100 * (1.10) ** (np.arange(n) / n)      # +10% -> RS line rising to new highs
    high, low = stock * 1.001, stock * 0.999
    vol = np.full(n, 1e6)
    f = compute_features(stock, high, low, vol, n - 1, bench_close=bench, lookbacks=(126,))
    assert f["rs_at_high_126"] > 0.99               # RS line at a new high
    assert f["rs_line_slope_126"] > 0               # RS rising


# ---- #2 group strength ----

def test_group_strength_leads_when_stock_and_sector_strong():
    n = 200
    bench = 100 * (1.05) ** (np.arange(n) / n)
    sector = 100 * (1.20) ** (np.arange(n) / n)     # sector beats market
    stock = 100 * (1.40) ** (np.arange(n) / n)      # stock beats sector
    g = group_strength_features(stock, sector, bench, n - 1)
    assert g["sector_rs_126"] > 0                    # stock leads its group
    assert g["group_strength_126"] > 0               # group leads the market


def test_group_strength_tags_are_valid_motivations():
    n = 200
    g = group_strength_features(
        100 * (1.2) ** (np.arange(n) / n), 100 * (1.1) ** (np.arange(n) / n),
        100 * (1.05) ** (np.arange(n) / n), n - 1)
    rows = catalog_rows(list(g), branch="price_volume")   # must not raise (fail-closed)
    assert all(r["motivation"] in MOTIVATIONS for r in rows)


# ---- #7 weekly resample ----

def test_weekly_resample_shape_and_aggregation():
    dates = pd.bdate_range("2020-01-06", periods=20)     # starts Monday -> exactly 4 full weeks
    close = np.arange(1, 21, dtype=float)
    wk = resample_weekly(dates, close, close + 0.5, close - 0.5, close, np.full(20, 100.0))
    assert len(wk) == 4
    assert wk["close"].iloc[0] == 5.0                    # last day of week 1 (5 business days)
    assert wk["high"].iloc[0] == 5.5 and wk["low"].iloc[0] == 0.5
    assert wk["volume"].iloc[0] == 500.0                 # 5 days x 100


def test_weekly_features_reuse_the_same_family():
    # the SAME compute_features runs on weekly bars (timeframe-agnostic)
    dates = pd.bdate_range("2018-01-01", periods=600)
    close, high, low, volume = _series(600, seed=3)
    wk = resample_weekly(dates, close, high, low, close, volume)
    fw = compute_features(wk["close"].to_numpy(), wk["high"].to_numpy(),
                          wk["low"].to_numpy(), wk["volume"].to_numpy(), len(wk) - 1)
    assert "atr_pct_21" in fw and "base_depth_21" in fw   # families work on weekly too


# ---- PIT integrity for the new daily features ----

def test_new_features_are_future_invariant():
    close, high, low, volume = _series(seed=5)
    bench = 100.0 * np.cumprod(1 + np.random.default_rng(9).normal(0.0002, 0.008, len(close)))
    assert_future_invariant(
        compute_features,
        {"close": close, "high": high, "low": low, "volume": volume, "bench_close": bench},
        i=380,
    )
