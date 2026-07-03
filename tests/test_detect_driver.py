"""Lineage end-to-end: the driver forward-fills excluded bars so no phantom move is seeded."""
import numpy as np

from gws.phase_a1.detect_driver import detect_moves_clean


def _rising(n=400):
    return 100 * np.cumprod(1 + np.full(n, 0.004))     # clean uptrend, no real trough late


def test_excluded_corrupt_bar_does_not_seed_a_phantom_move():
    close = _rising()
    dates = list(range(len(close)))
    volume = np.full(len(close), 1e6)

    # inject a corrupted -80% cliff at day 250 (a phantom_zero-style glitch) and exclude it
    corrupt = close.copy()
    corrupt[250] *= 0.2
    high, low = corrupt * 1.01, corrupt * 0.99

    *_, dirty = detect_moves_clean(high, low, corrupt, volume, dates, exception_spans=[])
    *_, clean = detect_moves_clean(high, low, corrupt, volume, dates, exception_spans=[(250, 250)])

    # the corrupt bar manufactures a deep trough at ~250 when NOT excluded; excluding + forward-
    # filling removes it, so no move anchors at that bar.
    dirty_troughs = {m.trough_idx for ms in dirty.values() for m in ms}
    clean_troughs = {m.trough_idx for ms in clean.values() for m in ms}
    assert any(248 <= t <= 251 for t in dirty_troughs)
    assert not any(248 <= t <= 251 for t in clean_troughs)


def test_untraded_zero_volume_bar_is_neutralized():
    close = _rising()
    dates = list(range(len(close)))
    volume = np.full(len(close), 1e6)
    close[300] *= 0.5                      # a glitch on a zero-volume (untraded) bar
    volume[300] = 0                        # actually-traded-bars rule should neutralize it
    high, low = close * 1.01, close * 0.99
    *_, moves = detect_moves_clean(high, low, close, volume, dates)
    assert not any(299 <= m.trough_idx <= 301 for ms in moves.values() for m in ms)


def test_leading_phantom_zero_bars_are_trimmed_not_seeded():
    # C-3: a phantom-zero series start (excluded) must be trimmed, never seed an infinite move.
    close = _rising()
    close[:5] = 0.001
    dates = list(range(len(close)))
    volume = np.full(len(close), 1e6)
    high, low = close * 1.01, close * 0.99
    _, c, h, lo, _, moves = detect_moves_clean(high, low, close, volume, dates, exception_spans=[(0, 4)])
    assert np.isfinite(c).all() and (c > 0).all()
    mags = [m.magnitude for ms in moves.values() for m in ms]
    assert all(m < 100 for m in mags)          # no +5,000,000% phantom from a ~0 trough


def test_nan_high_is_forward_filled_not_left_to_poison_atr():
    # C-2: a NaN high on a mid-series bar must be neutralized, not left to NaN the recursive ATR.
    close = _rising()
    dates = list(range(len(close)))
    volume = np.full(len(close), 1e6)
    high, low = close * 1.01, close * 0.99
    high[200] = np.nan
    _, c, h, lo, _, moves = detect_moves_clean(high, low, close, volume, dates)
    assert np.isfinite(h).all() and np.isfinite(c).all()
