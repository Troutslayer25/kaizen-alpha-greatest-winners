"""Daily -> weekly OHLCV resampling (multi-timeframe support).

Trend signals are often cleaner on the weekly timeframe (less noise; weekly MA / weekly RS
are distinct, well-used concepts). The feature families are timeframe-agnostic — they take a
price/volume series — so computing them on weekly-resampled bars roughly doubles the neutral
net for free, with no new feature code. This helper produces the weekly bars; A2 runs the
SAME families on both daily and weekly series.

Resampling is causal (a week's bar uses only that week's days), so PIT integrity is preserved:
a feature computed as of a weekly bar uses only data up to that week's close.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def resample_weekly(dates, open_, high, low, close, volume) -> pd.DataFrame:
    """Resample daily OHLCV to weekly (week ending Friday). Returns a DataFrame indexed by
    week-end date with columns open/high/low/close/volume. Partial final weeks are kept
    (they use only the days that occurred — causal)."""
    df = pd.DataFrame({
        "open": np.asarray(open_, float), "high": np.asarray(high, float),
        "low": np.asarray(low, float), "close": np.asarray(close, float),
        "volume": np.asarray(volume, float),
    }, index=pd.to_datetime(dates))
    agg = df.resample("W-FRI").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
    }).dropna(subset=["close"])
    return agg
