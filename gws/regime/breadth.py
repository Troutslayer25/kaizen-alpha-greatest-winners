"""Factor 2 — market breadth (computable from price data across the full window).

Breadth is the strongest, most data-available context factor: the balance of stocks
making new multi-period highs vs lows (normalized by issues) plus the share above
long/short moving averages, filtered to the eligible universe. Computed daily from a
wide close matrix; never derived from move-outcome data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_breadth(close_wide: pd.DataFrame, *, high_low_window: int = 252,
                    sma_periods=(50, 200), eligible_wide: pd.DataFrame | None = None) -> pd.DataFrame:
    """close_wide: index=date, columns=ticker_id, values=adjusted close (NaN where absent).

    eligible_wide (optional, same shape, boolean): mask of universe eligibility per
    date/ticker — ineligible cells are excluded from the counts. Returns daily breadth
    metrics and net_new_high_pct (the Factor-2 raw score, in [-1, 1])."""
    cw = close_wide.where(eligible_wide) if eligible_wide is not None else close_wide
    n_issues = cw.notna().sum(axis=1).replace(0, np.nan)
    out = pd.DataFrame(index=cw.index)

    for p in sma_periods:
        sma = cw.rolling(p, min_periods=p).mean()
        out[f"pct_above_sma{p}"] = (cw > sma).sum(axis=1) / n_issues

    roll_max = cw.rolling(high_low_window, min_periods=high_low_window).max()
    roll_min = cw.rolling(high_low_window, min_periods=high_low_window).min()
    new_high = (cw >= roll_max).sum(axis=1)
    new_low = (cw <= roll_min).sum(axis=1)
    out["new_high"] = new_high
    out["new_low"] = new_low
    out["net_new_high_pct"] = (new_high - new_low) / n_issues
    return out
