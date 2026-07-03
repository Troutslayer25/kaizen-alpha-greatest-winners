"""Vectorized per-ticker feature computation (compute aspect — the algorithmic scale win).

The per-point builder recomputes each rolling statistic per sample point; computing the rolling
arrays ONCE per ticker and indexing the points is the ~10-25x win the review flagged. Doing it
wrong silently changes features — the exact bug class this study guards against — so every
vectorized feature is GATED on numeric equality with the windowed per-point implementation
(gws.validation.feature_equality). This module implements the families that are EXACTLY
reproducible (rolling max/min are order-independent) plus rolling-mean families; the equality
harness proves each before it is trusted. Families that resist clean vectorization (polyfit
slopes, CMF, pullback logic) stay on the per-point path until they pass the same gate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from gws.phase_a2.features_price_volume import DEFAULT_LOOKBACKS, MA_PERIODS

# The families proven bit/numeric-equal and served from the vectorized path.
VECTORIZED_FIELDS = ("dist_from_high", "dist_from_low", "base_depth", "range_position",
                     "price_to_ma")


def compute_features_vectorized(close, *, lookbacks=DEFAULT_LOOKBACKS,
                                ma_periods=MA_PERIODS) -> dict:
    """Return {feature_name: full-length array}, one value per date, for the vectorized families.
    Warm-up positions (window not fully available) are NaN — matching the per-point omission."""
    close = np.asarray(close, float)
    s = pd.Series(close)
    px = close
    out: dict[str, np.ndarray] = {}
    for lb in lookbacks:
        rmax = s.rolling(lb).max().to_numpy()
        rmin = s.rolling(lb).min().to_numpy()
        out[f"dist_from_high_{lb}"] = np.where(rmax > 0, px / rmax - 1.0, np.nan)
        out[f"dist_from_low_{lb}"] = np.where(rmin > 0, px / rmin - 1.0, np.nan)
        out[f"base_depth_{lb}"] = np.where(rmax > 0, (rmax - rmin) / rmax, np.nan)
        out[f"range_position_{lb}"] = np.where(rmax > rmin, (px - rmin) / (rmax - rmin), np.nan)
    for p in ma_periods:
        rma = s.rolling(p).mean().to_numpy()
        out[f"price_to_ma_{p}"] = np.where(rma > 0, px / rma - 1.0, np.nan)
    return out
