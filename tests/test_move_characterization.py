"""Move classification substrate: rich outcome descriptors + PIT inception context."""
import types

import numpy as np

from gws.phase_a1.move_characterization import (DESCRIPTOR_FIELDS, INCEPTION_FIELDS,
                                               characterize_move, inception_context)


def _series(seed=0, n=420, trough=300, peak=390):
    rng = np.random.default_rng(seed)
    close = np.empty(n)
    close[:trough + 1] = np.linspace(100, 80, trough + 1) + rng.normal(0, 0.3, trough + 1)  # base + decline
    close[trough + 1:peak + 1] = np.linspace(80, 160, peak - trough) + rng.normal(0, 0.3, peak - trough)
    close[peak + 1:] = np.linspace(160, 140, n - peak - 1) + rng.normal(0, 0.3, n - peak - 1)
    close = np.abs(close)
    high, low = close * 1.01, close * 0.99
    volume = rng.integers(1e6, 5e6, n).astype(float)
    bench = 100 * np.cumprod(1 + rng.normal(0, 0.005, n))
    move = types.SimpleNamespace(trough_idx=trough, peak_idx=peak)
    return move, close, high, low, volume, bench


def test_characterize_emits_all_descriptor_fields():
    move, close, high, low, vol, bench = _series()
    d = characterize_move(move, close, high, low, volume=vol, bench_close=bench)
    assert set(DESCRIPTOR_FIELDS).issubset(d.keys())
    assert d["magnitude"] > 0.5 and d["duration_days"] == 90    # ~80->160 over 90 days
    assert 0 <= d["up_day_share"] <= 1
    assert d["big_day_count"] >= 0
    assert -1.0 <= d["front_loaded_ratio"] <= 2.0              # clipped (quant M)
    assert d["annualized_return"] <= 1e4                       # capped, not 1e15


def test_trend_quality_bounded_and_discriminates():
    import types
    big = np.linspace(100, 220, 181)              # smooth +120% over 180 bars -> a valid trend
    qb = characterize_move(types.SimpleNamespace(trough_idx=0, peak_idx=180), big)["trend_quality"]
    small = np.linspace(100, 103, 3)              # +3% over 2 bars -> noise, not a trend
    qs = characterize_move(types.SimpleNamespace(trough_idx=0, peak_idx=2), small)["trend_quality"]
    assert 0.0 <= qs < 0.3 < 0.7 < qb <= 1.0


def test_overnight_gaps_from_opens():
    move, close, high, low, vol, bench = _series()
    open_ = close.copy()
    t = move.trough_idx + 10
    open_[t] = close[t - 1] * 1.12                       # +12% overnight gap up
    d = characterize_move(move, close, high, low, volume=vol, bench_close=bench, open_=open_)
    assert d["overnight_gap_count"] >= 1 and d["largest_overnight_gap"] >= 0.10
    assert np.isnan(characterize_move(move, close)["overnight_gap_count"])   # NaN without opens


def test_inception_context_emits_all_fields_and_is_finite():
    move, close, high, low, vol, bench = _series()
    ctx = inception_context(move, close, high, low, volume=vol, bench_close=bench)
    assert set(INCEPTION_FIELDS) == set(ctx.keys())
    # F3: every field must be genuinely COMPUTED (finite), not vacuously NaN — a warm-up regression
    # that NaN'd everything would pass the invariance test but fill the catalog with NULLs.
    assert all(np.isfinite(v) for v in ctx.values()), [k for k, v in ctx.items() if not np.isfinite(v)]


def test_inception_context_depends_on_past_and_has_warmup_boundary():
    # F3: values must CHANGE when pre-trough bars change (proves they're not constants), and the
    # SMA-200 field is NaN one bar before its window is available and finite exactly at it.
    move, close, high, low, vol, bench = _series(seed=3)
    base = inception_context(move, close)["incept_price_to_sma50"]
    close2 = close.copy(); close2[:move.trough_idx] *= 1.3
    assert inception_context(move, close2)["incept_price_to_sma50"] != base

    import types
    long = np.abs(100 * np.cumprod(1 + np.random.default_rng(4).normal(0, 0.01, 260)))
    assert np.isnan(inception_context(types.SimpleNamespace(trough_idx=198), long)["incept_price_to_sma200"])
    assert np.isfinite(inception_context(types.SimpleNamespace(trough_idx=199), long)["incept_price_to_sma200"])


def test_inception_context_is_future_invariant():
    # THE bias-free guarantee: the tape-state AT the trough must not change when any bar AFTER
    # the trough is mutated. Proves inception context is safe to query against without look-ahead.
    move, close, high, low, vol, bench = _series(seed=1)
    base = inception_context(move, close, high, low, volume=vol, bench_close=bench)
    rng = np.random.default_rng(9)
    ti = move.trough_idx
    mut = [a.copy() for a in (close, high, low, vol, bench)]
    for a in mut:
        a[ti + 1:] *= rng.uniform(0.3, 2.0, len(a) - ti - 1)
    after = inception_context(move, mut[0], mut[1], mut[2], volume=mut[3], bench_close=mut[4])
    for k in base:
        assert (np.isnan(base[k]) and np.isnan(after[k])) or base[k] == after[k], f"{k} leaked future"


def test_outcome_descriptors_do_change_with_the_move_path():
    # sanity: shape descriptors legitimately depend on trough..peak (they ARE post-hoc outcomes)
    move, close, high, low, vol, bench = _series(seed=2)
    base = characterize_move(move, close)
    close2 = close.copy()
    close2[move.trough_idx + 1:move.peak_idx] *= 1.5     # change the path to the peak
    after = characterize_move(move, close2)
    assert base["smoothness"] != after["smoothness"] or base["max_intra_drawdown"] != after["max_intra_drawdown"]
