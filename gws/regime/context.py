"""Market-context assembly (regime_daily) — price-only factors available now.

Builds the daily context frame from the factors computable without options/credit
data: Factor 2 (breadth) and the trend anchor. Factor 1 (equity/options) and Factor 3
(credit) are left NULL until the Phase 0 audit confirms their data start dates; the
composite is therefore a placeholder over the available factors and is re-weighted in
Phase B1. Never a discovery-phase filter — it travels with each move as a snapshot.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from gws.regime.breadth import compute_breadth


def trend_anchor(bench_close, ma_period: int = 200) -> pd.Series:
    """Binary flag: broad index above its long-term MA. NaN during MA warm-up -> False."""
    s = pd.Series(np.asarray(bench_close, float))
    ma = s.rolling(ma_period, min_periods=ma_period).mean()
    return (s > ma).fillna(False)


def build_regime_daily(close_wide: pd.DataFrame, bench_close, *, high_low_window: int = 252,
                       anchor_ma: int = 200, eligible_wide: pd.DataFrame | None = None) -> pd.DataFrame:
    breadth = compute_breadth(close_wide, high_low_window=high_low_window, eligible_wide=eligible_wide)
    df = pd.DataFrame(index=close_wide.index)
    df["f1_score"] = np.nan          # equity/options — pending Phase 0 data start
    df["f3_score"] = np.nan          # credit — pending Phase 0 data start
    df["f2_score"] = breadth["net_new_high_pct"]
    df["trend_anchor"] = trend_anchor(bench_close, anchor_ma).to_numpy()
    # composite over available factors only (currently F2); scaled to ~[-10, 10]; B1 re-weights
    df["composite_score"] = (df["f2_score"] * 10.0).clip(-10, 10)
    df["regime_label"] = pd.cut(df["composite_score"], bins=[-np.inf, -3, 3, np.inf],
                                labels=["risk_off", "neutral", "risk_on"])
    df["score_version"] = "v1_breadth_anchor"
    return df
