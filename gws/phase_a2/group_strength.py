"""Group / sector strength features (Phase A2).

"Leading stocks in leading groups" is a documented trend-following edge: a stock's strength
relative to its OWN sector, and the sector's strength relative to the market. Measured
neutrally (relative strength vs a reference series) — the study discovers whether group
context matters; it is not asserted.

Per observation:
  - sector_rs_{lb}        : stock return vs its sector return (is the stock leading its group?)
  - sector_rs_slope_{lb}  : slope of the stock/sector RS line
  - group_strength_{lb}   : sector return vs the broad-market return (is the group leading?)

Requires sector/industry classification + a sector return series (Phase 0 data capture; Norgate
carries historical classifications, so this is potentially deep-history-capable — confirmed by
the Phase 0 audit). PIT: uses only data on or before `i`.
"""
from __future__ import annotations

import numpy as np

DEFAULT_LOOKBACKS = (21, 63, 126)


def _rs_return(series, ref, i, lb):
    series = np.asarray(series, float); ref = np.asarray(ref, float)
    if i - lb >= 0 and series[i - lb] > 0 and ref[i] > 0 and ref[i - lb] > 0:
        return float((series[i] / series[i - lb]) / (ref[i] / ref[i - lb]) - 1.0)
    return None


def _rs_slope(series, ref, i, lb):
    series = np.asarray(series, float); ref = np.asarray(ref, float)
    if i - lb + 1 < 0 or lb < 2:
        return None
    rs = np.where(ref > 0, series / ref, np.nan)[i - lb + 1: i + 1]
    if len(rs) != lb or not np.isfinite(rs).all() or rs.mean() == 0:
        return None
    return float(np.polyfit(np.arange(lb), rs, 1)[0] / abs(rs.mean()))


def group_strength_features(stock_close, sector_close, bench_close, i, *,
                            lookbacks=DEFAULT_LOOKBACKS) -> dict:
    """Stock-vs-sector RS (`sector_rs_*`) and sector-vs-market strength (`group_strength_*`)."""
    feats: dict[str, float] = {}
    for lb in lookbacks:
        rs = _rs_return(stock_close, sector_close, i, lb)
        if rs is not None:
            feats[f"sector_rs_{lb}"] = rs
        sl = _rs_slope(stock_close, sector_close, i, lb)
        if sl is not None:
            feats[f"sector_rs_slope_{lb}"] = sl
        gs = _rs_return(sector_close, bench_close, i, lb)
        if gs is not None:
            feats[f"group_strength_{lb}"] = gs
    return feats
