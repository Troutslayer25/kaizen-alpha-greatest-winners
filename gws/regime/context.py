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
    """Broad index above its long-term MA: 1.0 above, 0.0 below, NaN during MA warm-up.

    Warm-up is UNKNOWN, not below (review m-8): mapping the 200-day warm-up NaN to False
    silently labels the earliest bars 'risk-off'. NaN keeps the ambiguity honest."""
    s = pd.Series(np.asarray(bench_close, float))
    ma = s.rolling(ma_period, min_periods=ma_period).mean()
    res = pd.Series(np.where(s.to_numpy() > ma.to_numpy(), 1.0, 0.0), index=s.index)
    res[ma.isna().to_numpy()] = np.nan
    return res


def build_regime_daily(close_wide: pd.DataFrame, bench_close, *, high_low_window: int = 252,
                       anchor_ma: int = 200, eligible_wide: pd.DataFrame | None = None,
                       require_eligible: bool = True) -> pd.DataFrame:
    # Breadth over a survivor-only close matrix inflates deep-history breadth (dead names never
    # drag the count down), which biases regime labels bullish exactly when it matters. The
    # production path MUST pass the PIT eligibility mask (review m-8 / PIT 3.5).
    if require_eligible and eligible_wide is None:
        raise ValueError(
            "build_regime_daily: eligible_wide is required — pass the PIT mask from "
            "gws.universe_eligibility, or set require_eligible=False for a single-cohort test")
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
    # PER-DATE version string (review m-8): the composite's MEANING changes when F1/F3 begin
    # mid-history, so a single version label over the whole series is a lie. Stamp per row by
    # which factors are actually present, so pre-1990 breadth-only scores are never silently
    # compared to later three-factor scores under one string.
    have3 = df[["f1_score", "f3_score"]].notna().all(axis=1)
    df["score_version"] = np.where(have3, "v3_breadth_f1_f3", "v1_breadth_anchor")
    return df
