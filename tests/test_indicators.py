import numpy as np

from gws.common.indicators import true_range, wilder_atr, sma, ema


def test_true_range_first_bar_is_high_low():
    high = np.array([10.0, 11, 12])
    low = np.array([9.0, 10, 11])
    close = np.array([9.5, 10.5, 11.5])
    tr = true_range(high, low, close)
    assert tr[0] == 1.0  # prev_close seeded with close[0]


def test_atr_constant_series():
    # Constant 1.0 true range every bar -> ATR converges to 1.0 after the seed.
    n = 50
    close = np.full(n, 100.0)
    high = close + 0.5
    low = close - 0.5
    atr = wilder_atr(high, low, close, period=14)
    assert np.isnan(atr[:13]).all()
    assert np.isclose(atr[13], 1.0)        # seed = mean of first 14 TRs (all 1.0)
    assert np.isclose(atr[-1], 1.0)


def test_sma_basic():
    v = np.arange(1, 11, dtype=float)      # 1..10
    out = sma(v, 3)
    assert np.isnan(out[:2]).all()
    assert np.isclose(out[2], 2.0)         # mean(1,2,3)
    assert np.isclose(out[-1], 9.0)        # mean(8,9,10)


def test_ema_seed_is_sma():
    v = np.arange(1, 21, dtype=float)
    out = ema(v, 5)
    assert np.isnan(out[:4]).all()
    assert np.isclose(out[4], 3.0)         # SMA of first 5 = mean(1..5)
