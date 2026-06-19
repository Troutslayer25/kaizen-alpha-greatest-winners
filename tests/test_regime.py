import numpy as np
import pandas as pd

from gws.regime.breadth import compute_breadth
from gws.regime.context import trend_anchor, build_regime_daily

N = 320
LATE = 300


def _wide(direction):
    col = np.linspace(100, 200, N) if direction == "up" else np.linspace(200, 100, N)
    return pd.DataFrame({tk: col.copy() for tk in range(5)})


def test_breadth_bullish_when_all_rising():
    b = compute_breadth(_wide("up"))
    assert np.isclose(b["net_new_high_pct"].iloc[LATE], 1.0)
    assert np.isclose(b["pct_above_sma200"].iloc[LATE], 1.0)


def test_breadth_bearish_when_all_falling():
    b = compute_breadth(_wide("down"))
    assert np.isclose(b["net_new_high_pct"].iloc[LATE], -1.0)
    assert b["pct_above_sma200"].iloc[LATE] < 0.05


def test_trend_anchor_tracks_long_ma():
    up = np.linspace(100, 200, N)
    down = np.linspace(200, 100, N)
    assert trend_anchor(up).iloc[LATE]
    assert not trend_anchor(down).iloc[LATE]


def test_regime_daily_assembles_and_labels():
    bench = np.linspace(100, 200, N)
    df = build_regime_daily(_wide("up"), bench)
    assert {"f1_score", "f2_score", "f3_score", "trend_anchor", "composite_score",
            "regime_label"}.issubset(df.columns)
    assert df["f1_score"].isna().all() and df["f3_score"].isna().all()   # pending Phase-0 data
    assert df["regime_label"].iloc[LATE] == "risk_on"
    assert bool(df["trend_anchor"].iloc[LATE]) is True
