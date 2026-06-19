"""Branch-1 (price/volume) pre-move feature extraction (Phase A2).

Every feature is a pure function of a single ticker's OHLCV series and an as-of
index `i`, computed using ONLY data on or before `i` (close[: i+1]). This is the
structural guarantee behind PIT integrity: see gws/common/pit_audit.py, which
mechanically proves each feature is invariant to any change in the future bars.

Feature names are neutral and descriptive (no named-indicator references), per the
discovery-first / bias-control requirements. Each feature is computed over multiple
lookback windows so the predictive horizon is discovered, not assumed. A feature is
omitted (not zero-filled) when its lookback window is not fully available at `i`.

These are intentionally re-implemented clean (provenance Tier A) rather than imported
from the production pipeline, so no framework-tuned parameter is inherited.
"""
from __future__ import annotations

import numpy as np

DEFAULT_LOOKBACKS = (21, 42, 63, 126)
MA_PERIODS = (20, 50, 150, 200)


def _window(a, i, lb):
    """The lb-length slice ending at i, or None if not fully available."""
    if i - lb + 1 < 0:
        return None
    return a[i - lb + 1 : i + 1]


def _mean_true_range(high, low, close, i, lb):
    if i - lb < 0:
        return None
    h = high[i - lb + 1 : i + 1]
    l = low[i - lb + 1 : i + 1]
    pc = close[i - lb : i]  # previous closes aligned to the window
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return float(tr.mean())


def compute_features(close, high, low, volume, i, *, bench_close=None,
                     lookbacks=DEFAULT_LOOKBACKS):
    """Return {feature_name: value} for the observation at index `i`.

    Uses only close[: i+1] (and the equivalent for the other series). `bench_close`
    enables relative-strength features; omit it to skip them.
    """
    close = np.asarray(close, float)
    high = np.asarray(high, float)
    low = np.asarray(low, float)
    volume = np.asarray(volume, float)
    px = close[i]
    feats: dict[str, float] = {}
    if px <= 0:
        return feats

    for lb in lookbacks:
        w = _window(close, i, lb)
        if w is not None:
            mx, mn = float(w.max()), float(w.min())
            feats[f"dist_from_high_{lb}"] = px / mx - 1.0 if mx > 0 else np.nan
            feats[f"dist_from_low_{lb}"] = px / mn - 1.0 if mn > 0 else np.nan
            rets = np.diff(np.log(w)) if (w > 0).all() else np.array([np.nan])
            feats[f"ret_std_{lb}"] = float(np.std(rets, ddof=1)) if len(rets) > 1 else np.nan
        atr = _mean_true_range(high, low, close, i, lb)
        if atr is not None:
            feats[f"atr_pct_{lb}"] = atr / px

        vw = _window(volume, i, lb)
        prior = _window(volume, i - lb, lb)
        if vw is not None and prior is not None and prior.mean() > 0:
            feats[f"vol_ratio_{lb}"] = float(vw.mean() / prior.mean())
        cw = _window(close, i, lb + 1)
        vw2 = _window(volume, i, lb)
        if cw is not None and vw2 is not None:
            dr = np.diff(cw)
            up = vw2[dr > 0].sum()
            dn = vw2[dr < 0].sum()
            feats[f"updown_vol_{lb}"] = float(up / dn) if dn > 0 else np.nan

    # range tightness: short-window range vs longer-window range (< 1 = tightening)
    short = _mean_true_range(high, low, close, i, lookbacks[0])
    longw = _mean_true_range(high, low, close, i, lookbacks[-1])
    if short is not None and longw is not None and longw > 0:
        feats["range_tightness"] = short / longw

    # price relative to moving averages, and MA compression
    ma_vals = {}
    for p in MA_PERIODS:
        w = _window(close, i, p)
        if w is not None:
            ma = float(w.mean())
            ma_vals[p] = ma
            feats[f"price_to_ma_{p}"] = px / ma - 1.0 if ma > 0 else np.nan
    if len(ma_vals) >= 2:
        vals = np.array(list(ma_vals.values()))
        feats["ma_compression"] = float((vals.max() - vals.min()) / px)

    # relative strength vs benchmark over each lookback
    if bench_close is not None:
        bench_close = np.asarray(bench_close, float)
        for lb in lookbacks:
            if i - lb >= 0 and close[i - lb] > 0 and bench_close[i] > 0 and bench_close[i - lb] > 0:
                stock_ret = close[i] / close[i - lb]
                bench_ret = bench_close[i] / bench_close[i - lb]
                feats[f"rel_strength_{lb}"] = float(stock_ret / bench_ret - 1.0)

    return feats
