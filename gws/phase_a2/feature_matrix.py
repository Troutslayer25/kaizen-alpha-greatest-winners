"""Wide feature-matrix builder (Phase A2).

Turns a set of observation points (ticker_id, as_of_index) into a wide numeric matrix
by calling the (ticker_id, as_of_date)-keyed feature functions once per point. This is
the ML-consumable materialization referenced in blueprint T3; the long per-value store
remains the audit/lineage record. Because every point goes through the same feature
calls, extraction is identical for setups, controls, and sampled points by construction.

The matrix includes BOTH the Branch-1 price/volume features AND the generic/auto feature
bank by default (`include_generic=True`). Wiring the generic bank in is a bias control,
not an optimization: practitioner-recognizable features must compete against
framework-neutral descriptors, or the Gate A3->A4 motivation cross-tab is trivially
all-practitioner (KA_AUDITOR_PROMPTS Auditor 4 §28).
"""
from __future__ import annotations

import pandas as pd

from gws.phase_a2.features_price_volume import compute_features, DEFAULT_LOOKBACKS
from gws.phase_a2.generic_features import compute_generic_features


def build_feature_matrix(points: pd.DataFrame, series_by_ticker: dict, *,
                         bench_by_ticker: dict | None = None,
                         lookbacks=DEFAULT_LOOKBACKS,
                         include_generic: bool = True) -> pd.DataFrame:
    """Compute features for each (ticker_id, as_of_index) point.

    `series_by_ticker[tk]` is a dict with 'close','high','low','volume' arrays.
    Returns a DataFrame aligned 1:1 with `points` (same index), one column per feature.
    Includes the generic/auto bank unless `include_generic=False`.
    """
    recs = []
    for row in points.itertuples():
        s = series_by_ticker[row.ticker_id]
        bench = bench_by_ticker.get(row.ticker_id) if bench_by_ticker else None
        feats = compute_features(
            s["close"], s["high"], s["low"], s["volume"], row.as_of_index,
            bench_close=bench, lookbacks=lookbacks)
        if include_generic:
            feats = {**feats, **compute_generic_features(
                s["close"], s["high"], s["low"], s["volume"], row.as_of_index)}
        recs.append(feats)
    return pd.DataFrame(recs, index=points.index)
