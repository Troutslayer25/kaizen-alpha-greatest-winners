import numpy as np

from gws.phase_a1.move_detector_mfe import detect_moves_mfe, detect_moves_multiscale
from gws.phase_a1.trough_detector import detect_moves as detect_atr_swing


def _ohlc(c):
    c = np.asarray(c, float)
    return c * 1.003, c * 0.997, c


def _clean_winner():           # smooth 100 -> 200
    return np.concatenate([np.full(30, 100.0), np.linspace(100, 200, 90)])


def _wild_winner():            # same net 100 -> 200, violent internal swings
    wp = [100, 130, 112, 155, 130, 185, 160, 200]
    return np.concatenate([np.full(30, 100.0)]
                          + [np.linspace(wp[i], wp[i + 1], 14) for i in range(len(wp) - 1)])


def test_mfe_catches_lowvol_move_that_atr_swing_misses():
    # The debate's case: a real ~7% move in a quiet stock. ATR-swing's 10% floor misses it.
    c = np.concatenate([np.full(40, 100.0), np.linspace(100, 107, 30), np.linspace(107, 103, 15)])
    h, l, _ = _ohlc(c)
    assert len(detect_atr_swing(h, l, c)) == 0                     # floored out
    mfe = detect_moves_mfe(h, l, c, trail_atr=3.0)
    assert len(mfe) >= 1
    assert 0.05 <= max(m.magnitude for m in mfe) <= 0.09           # captured at its true size


def test_wild_move_fragments_at_tight_scale_clean_does_not():
    hc, lc, c_clean = _ohlc(_clean_winner())
    hw, lw, c_wild = _ohlc(_wild_winner())
    clean = detect_moves_mfe(hc, lc, c_clean, trail_atr=2.0)
    wild = detect_moves_mfe(hw, lw, c_wild, trail_atr=2.0)
    assert len(clean) == 1                                         # clean stays whole
    assert len(wild) >= 3                                          # wild shatters into swing legs


def test_smoothness_separates_clean_from_wild_at_loose_scale():
    hc, lc, c_clean = _ohlc(_clean_winner())
    hw, lw, c_wild = _ohlc(_wild_winner())
    clean = detect_moves_mfe(hc, lc, c_clean, trail_atr=15.0)
    wild = detect_moves_mfe(hw, lw, c_wild, trail_atr=15.0)
    assert len(clean) == 1 and len(wild) == 1                      # both one big arc at loose scale
    assert clean[0].magnitude > 0.9 and wild[0].magnitude > 0.9    # same net magnitude
    assert clean[0].smoothness > 0.9                              # clean path
    assert wild[0].smoothness < 0.6                               # wild path
    assert wild[0].smoothness < clean[0].smoothness               # separated


def test_early_shakeout_stays_one_move_and_records_mae():
    # dip below the start before liftoff, within the band -> tolerated and recorded, not split.
    c = np.concatenate([np.full(30, 100.0), np.linspace(100, 101, 3),
                        np.linspace(101, 96, 5), np.linspace(96, 150, 45)])
    h, l, _ = _ohlc(c)
    moves = detect_moves_mfe(h, l, c, trail_atr=8.0)
    assert len(moves) == 1
    assert moves[0].mae > 0.03                                     # the sub-start dip is recorded
    assert moves[0].trough_idx <= 30                              # anchored at the original trough
    assert 0.45 <= moves[0].magnitude <= 0.55


def test_multiscale_returns_a_population_per_scale():
    hw, lw, c_wild = _ohlc(_wild_winner())
    res = detect_moves_multiscale(hw, lw, c_wild, scales=(2.0, 6.0, 15.0))
    assert set(res.keys()) == {2.0, 6.0, 15.0}
    # tightening the scale never reduces the move count (more swing legs surface)
    assert len(res[2.0]) >= len(res[15.0])
