import numpy as np

from gws.phase_a1.trough_detector import detect_moves


def _ohlc(close):
    close = np.asarray(close, float)
    return close * 1.0005, close * 0.9995, close  # high, low, close (tight spread)


def test_detects_single_clean_move():
    flat = np.full(60, 100.0)
    rise = 100.0 * (1.5) ** (np.arange(1, 41) / 40)   # 100 -> 150 over 40 days
    drop = np.linspace(150.0, 105.0, 20)               # >20% reversal from the peak
    close = np.concatenate([flat, rise, drop])
    high, low, _ = _ohlc(close)

    moves = detect_moves(high, low, close, atr_period=21, atr_mult=3.0,
                         min_abs_gain=0.10, min_duration=10, reversal_threshold=0.20)

    assert len(moves) >= 1
    m = moves[0]
    assert 0.40 <= m.trough_gain_pct <= 0.60
    assert m.peak_idx <= 100                  # peak is at the top of the rise (~day 99)
    assert not m.is_open                      # the 25%+ drop resolves the move
    assert 0.0 <= m.max_intra_drawdown < 0.05
    assert m.smoothness > 0.8                 # near-monotonic rise is "smooth"


def test_flat_series_no_moves():
    close = np.full(200, 100.0)
    high, low, _ = _ohlc(close)
    moves = detect_moves(high, low, close)
    assert moves == []
