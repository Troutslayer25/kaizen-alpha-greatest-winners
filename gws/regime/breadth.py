"""Factor 2 — market breadth (computable from price data across the full window).

Breadth is the strongest, most data-available context factor: the balance of stocks
making new multi-period highs vs lows (normalized by issues) plus the share above a
SWEEP of moving-average horizons, filtered to the eligible universe. Computed daily from a
wide close matrix; never derived from move-outcome data.

Swept breadth-MA surface (discovery-first, mirrors the stock-level MA-sweep decision):
instead of hardcoding a named horizon (e.g. "% above the 5-day MA", the FOMO indicator),
% of the universe above the N-day MA is computed across a SWEEP of N. The analysis treats
this as a response curve (signal vs MA length) — NOT N independent collinear features — to
discover which horizon of participation leads trend-momentum change, per regime. If the
short end wins it independently confirms the FOMO concept; if another horizon wins, novel.
Both tails matter (high % = froth, low % = capitulation). Price-derived -> deep-history
computable -> a full-study input.

Breadth term structure: the spread between short-horizon and long-horizon breadth
(`breadth_spread_<short>_<long>`) is itself a measurement. Short breadth rolling over while
long breadth holds = participation thinning at the fast timescale before the major trend
cracks — a candidate leading-divergence measure. Captured as a continuous gap, not a signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Pre-committed swept horizons for % above the N-day MA (the FOMO indicator generalized).
SWEEP_PERIODS = (5, 8, 10, 13, 21, 50, 100, 200)


def compute_breadth(close_wide: pd.DataFrame, *, high_low_window: int = 252,
                    sweep_periods=SWEEP_PERIODS, spread_pair: tuple[int, int] | None = None,
                    eligible_wide: pd.DataFrame | None = None) -> pd.DataFrame:
    """close_wide: index=date, columns=ticker_id, values=adjusted close (NaN where absent).

    eligible_wide (optional, same shape, boolean): mask of universe eligibility per
    date/ticker — ineligible cells are excluded from the counts.

    Returns daily breadth metrics: `pct_above_sma{N}` for each swept N (the response
    surface), the short/long breadth-term-structure spread, and net_new_high_pct (the
    Factor-2 raw score in [-1, 1]). `spread_pair` defaults to (min, max) of the sweep.
    """
    cw = close_wide.where(eligible_wide) if eligible_wide is not None else close_wide
    out = pd.DataFrame(index=cw.index)

    periods = sorted(set(sweep_periods))
    for p in periods:
        sma = cw.rolling(p, min_periods=p).mean()
        # Denominator counts ONLY issues whose SMA is defined on this date (review m-9). Counting
        # every issue-with-a-close — including those still in their MA warm-up, which compare
        # False — structurally depresses participation in heavy-new-listing periods (late-'90s,
        # 2020-21): exactly the regimes of interest.
        elig = cw.notna() & sma.notna()
        denom = elig.sum(axis=1).replace(0, np.nan)
        out[f"pct_above_sma{p}"] = ((cw > sma) & elig).sum(axis=1) / denom

    # breadth term structure: short-horizon minus long-horizon participation
    short_p, long_p = spread_pair if spread_pair is not None else (periods[0], periods[-1])
    if short_p in periods and long_p in periods and short_p != long_p:
        out[f"breadth_spread_{short_p}_{long_p}"] = (
            out[f"pct_above_sma{short_p}"] - out[f"pct_above_sma{long_p}"])

    roll_max = cw.rolling(high_low_window, min_periods=high_low_window).max()
    roll_min = cw.rolling(high_low_window, min_periods=high_low_window).min()
    elig_hl = cw.notna() & roll_max.notna()                       # only issues with a full window
    denom_hl = elig_hl.sum(axis=1).replace(0, np.nan)
    new_high = ((cw >= roll_max) & elig_hl).sum(axis=1)
    new_low = ((cw <= roll_min) & elig_hl).sum(axis=1)
    out["new_high"] = new_high
    out["new_low"] = new_low
    out["net_new_high_pct"] = (new_high - new_low) / denom_hl
    return out
