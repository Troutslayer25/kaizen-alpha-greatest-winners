"""Wide feature-matrix builder (Phase A2).

Turns a set of observation points (ticker_id, as_of_index) into a wide numeric matrix
by calling the (ticker_id, as_of_date)-keyed feature functions once per point. This is
the ML-consumable materialization referenced in blueprint T3; the long per-value store
remains the audit/lineage record. Because every point goes through the same
compute_features call, extraction is identical for setups, controls, and sampled
points by construction.
"""
from __future__ import annotations

import pandas as pd

from gws.phase_a2.features_price_volume import compute_features, DEFAULT_LOOKBACKS


def build_feature_matrix(points: pd.DataFrame, series_by_ticker: dict, *,
                         bench_by_ticker: dict | None = None,
                         lookbacks=DEFAULT_LOOKBACKS) -> pd.DataFrame:
    """Compute Branch-1 features for each (ticker_id, as_of_index) point.

    `series_by_ticker[tk]` is a dict with 'close','high','low','volume' arrays.
    Returns a DataFrame aligned 1:1 with `points` (same index), one column per feature.
    """
    recs = []
    for row in points.itertuples():
        s = series_by_ticker[row.ticker_id]
        bench = bench_by_ticker.get(row.ticker_id) if bench_by_ticker else None
        recs.append(compute_features(
            s["close"], s["high"], s["low"], s["volume"], row.as_of_index,
            bench_close=bench, lookbacks=lookbacks))
    return pd.DataFrame(recs, index=points.index)
