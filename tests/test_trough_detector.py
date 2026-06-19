import numpy as np

from gws.phase_a1.trough_detector import detect_moves


def _ohlc(close):
    close = np.asarray(close, float)
    return close * 1.0005, close * 0.9995, close  # high, low, close (tight spread)


def test_detects_single_clean_move():
    # Decline into a trough (so the trough sits past the ATR warm-up region, at a
    # bar where ATR is defined — no warm-up backfill), then a clean rise, then a
    # >20% drop that resolves the move.
    decline = np.linspace(100.0, 95.0, 40)            # trough at index 39
    rise = np.linspace(95.0, 145.0, 40)               # peak at index 79
    drop = np.linspace(145.0, 110.0, 20)              # ~24% reversal -> closes the move
    close = np.concatenate([decline, rise, drop])
    high, low, _ = _ohlc(close)

    moves = detect_moves(high, low, close, atr_period=21, atr_mult=3.0,
                         min_abs_gain=0.10, min_duration=10, reversal_threshold=0.20)

    assert len(moves) >= 1
    m = moves[0]
    assert 38 <= m.trough_idx <= 40          # trough localized at the actual low (~39)
    assert 0.45 <= m.trough_gain_pct <= 0.60
    assert not m.is_open                      # the 24% drop resolves the move
    assert 0.0 <= m.max_intra_drawdown < 0.05
    assert m.smoothness > 0.8                 # near-monotonic rise is "smooth"
    assert m.detection_system == "atr_swing"
    assert m.reversal_threshold == 0.20


def test_interior_pullback_drawdown_recorded():
    # A move with a real interior pullback (below the 20% reversal threshold) so the
    # drawdown accumulation is actually exercised, not trivially ~0.
    pre = np.linspace(112.0, 100.0, 30)               # decline into the trough (past ATR warm-up)
    up1 = np.linspace(100.0, 130.0, 30)
    pull = np.linspace(130.0, 117.0, 8)               # ~10% interior pullback (< 20%)
    up2 = np.linspace(117.0, 170.0, 40)
    drop = np.linspace(170.0, 120.0, 15)              # ~29% reversal -> closes the move
    close = np.concatenate([pre, up1, pull, up2, drop])
    high, low, _ = _ohlc(close)

    moves = detect_moves(high, low, close, reversal_threshold=0.20)
    assert len(moves) >= 1
    m = moves[0]
    assert 0.08 <= m.max_intra_drawdown <= 0.20       # captures the interior pullback


def test_non_positive_close_does_not_crash():
    # A phantom-zero adjusted_close inside the series must not produce inf/NaN crash.
    close = np.concatenate([np.linspace(100.0, 95.0, 40), np.linspace(95.0, 150.0, 40)])
    close[10] = 0.0                                    # injected bad row
    high, low, _ = _ohlc(close)
    moves = detect_moves(high, low, close)             # must not raise
    assert isinstance(moves, list)


def test_flat_series_no_moves():
    close = np.full(200, 100.0)
    high, low, _ = _ohlc(close)
    moves = detect_moves(high, low, close)
    assert moves == []
