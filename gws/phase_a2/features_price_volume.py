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
# CANONICAL-ONLY, NOT YET SWEPT. The MA family must be broadened to a swept window range
# {3,5,8,10,13,21,30,50,100,150,200} x {SMA,EMA} before A3 MA findings are accepted, so the
# predictive window is DISCOVERED, not assumed (otherwise discovery trivially re-finds 50/200
# — a feature-selection-contamination vector). Pre-commit the swept family in the A2 spec.
# See research/open_questions/moving_average_discovery.md.
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
                     lookbacks=DEFAULT_LOOKBACKS, exclude=frozenset()):
    """Return {feature_name: value} for the observation at index `i`.

    Uses only close[: i+1] (and the equivalent for the other series). `bench_close`
    enables relative-strength features; omit it to skip them.

    `exclude` (compute aspect): family prefixes to SKIP — the builder passes the families it will
    supply from the proven vectorized path (gws.phase_a2.features_vectorized), so they are not
    recomputed per point. End-to-end equality with the un-excluded build is unit-tested.
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
            if "dist_from_high" not in exclude:
                feats[f"dist_from_high_{lb}"] = px / mx - 1.0 if mx > 0 else np.nan
            if "dist_from_low" not in exclude:
                feats[f"dist_from_low_{lb}"] = px / mn - 1.0 if mn > 0 else np.nan
            rets = np.diff(np.log(w)) if (w > 0).all() else np.array([np.nan])
            feats[f"ret_std_{lb}"] = float(np.std(rets, ddof=1)) if len(rets) > 1 else np.nan
        atr = _mean_true_range(high, low, close, i, lb)
        if atr is not None:
            feats[f"atr_pct_{lb}"] = atr / px

        # Volume family — comprehensive FROM FIRST PRINCIPLES (levels, surge, up/down balance,
        # up/down extremes, accumulation share, trend, money flow). Designed to span the natural
        # ways to measure volume behaviour so that any volume-based accumulation signal — named
        # or not — can be discovered; NOT reverse-engineered to any specific practitioner rule.
        vw = _window(volume, i, lb)
        prior = _window(volume, i - lb, lb)
        if vw is not None and prior is not None and prior.mean() > 0:
            feats[f"vol_ratio_{lb}"] = float(vw.mean() / prior.mean())          # recent vs prior level (<1 = contraction)
        if vw is not None and vw.mean() > 0:
            feats[f"vol_surge_{lb}"] = float(volume[i] / vw.mean())             # today's volume vs recent average (RVOL)
            sl = np.polyfit(np.arange(lb), vw, 1)[0] if lb > 1 else 0.0
            feats[f"vol_trend_{lb}"] = float(sl / vw.mean())                    # normalized volume slope
        cw = _window(close, i, lb + 1)
        vw2 = _window(volume, i, lb)
        if cw is not None and vw2 is not None:
            dr = np.diff(cw)
            up_v = vw2[dr > 0]; dn_v = vw2[dr < 0]
            up = up_v.sum(); dn = dn_v.sum(); tot = vw2.sum()
            feats[f"updown_vol_{lb}"] = float(up / dn) if dn > 0 else np.nan    # up vs down volume balance
            if tot > 0:
                feats[f"accum_vol_share_{lb}"] = float(up / tot)               # share of volume on up days
            if up_v.size and dn_v.size and dn_v.max() > 0:
                feats[f"up_vs_down_vol_extreme_{lb}"] = float(up_v.max() / dn_v.max())  # biggest buying vs biggest selling day
        # Chaikin money flow: close-location-value weighted volume (accumulation/distribution)
        hw = _window(high, i, lb); lw = _window(low, i, lb); ccw = _window(close, i, lb)
        if hw is not None and lw is not None and ccw is not None and vw is not None:
            rng = hw - lw
            clv = np.where(rng > 0, ((ccw - lw) - (hw - ccw)) / rng, 0.0)
            if vw.sum() > 0:
                feats[f"cmf_{lb}"] = float((clv * vw).sum() / vw.sum())

    # Consolidation / base-structure family (first principles): how deep the range, where
    # price sits in it, whether volatility is contracting, how tight the action is. Measures
    # base/contraction structure neutrally — clustering finds the base-like shapes; no named
    # pattern (e.g. VCP) is asserted.
    for lb in lookbacks:
        w = _window(close, i, lb)
        if w is None:
            continue
        mx, mn = float(w.max()), float(w.min())
        if mx > 0 and "base_depth" not in exclude:
            feats[f"base_depth_{lb}"] = (mx - mn) / mx                  # range depth (drawdown across the base)
        if mx > mn and "range_position" not in exclude:
            feats[f"range_position_{lb}"] = (px - mn) / (mx - mn)       # where in the range price sits (near 1 = top/breakout area)
        # volatility contraction: recent-half ATR vs earlier-half ATR (<1 = contracting)
        half = lb // 2
        atr_recent = _mean_true_range(high, low, close, i, half)
        atr_earlier = _mean_true_range(high, low, close, i - half, half)
        if atr_recent is not None and atr_earlier is not None and atr_earlier > 0:
            feats[f"vol_contraction_{lb}"] = atr_recent / atr_earlier
        # tightness: share of days with daily range below the window-median range
        hw = _window(high, i, lb); lw = _window(low, i, lb)
        if hw is not None and lw is not None:
            rng = hw - lw
            med = np.median(rng)
            if med > 0:
                feats[f"tight_days_share_{lb}"] = float(np.mean(rng < med))

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
            ma_vals[p] = ma                                    # kept for ma_compression even if excluded
            if "price_to_ma" not in exclude:
                feats[f"price_to_ma_{p}"] = px / ma - 1.0 if ma > 0 else np.nan
    if len(ma_vals) >= 2:
        vals = np.array(list(ma_vals.values()))
        feats["ma_compression"] = float((vals.max() - vals.min()) / px)

    # Relative-strength family vs benchmark (the core leadership signal). Beyond simple
    # outperformance: the slope of the RS line, and whether the RS line is at a NEW HIGH —
    # RS-line-leads-price is a classic leading tell. (Rank-within-universe/sector needs the
    # cross-sectional panel and is added at extraction time, not here.)
    if bench_close is not None:
        bench_close = np.asarray(bench_close, float)
        rs_line = np.where(bench_close > 0, close / bench_close, np.nan)
        for lb in lookbacks:
            if i - lb >= 0 and close[i - lb] > 0 and bench_close[i] > 0 and bench_close[i - lb] > 0:
                stock_ret = close[i] / close[i - lb]
                bench_ret = bench_close[i] / bench_close[i - lb]
                feats[f"rel_strength_{lb}"] = float(stock_ret / bench_ret - 1.0)
            rw = _window(rs_line, i, lb)
            if rw is not None and np.isfinite(rw).all() and rw.mean() != 0:
                sl = np.polyfit(np.arange(lb), rw, 1)[0] if lb > 1 else 0.0
                feats[f"rs_line_slope_{lb}"] = float(sl / abs(rw.mean()))     # normalized RS-line slope
                mxr = rw.max()
                if mxr > 0:
                    feats[f"rs_at_high_{lb}"] = float(rw[-1] / mxr)            # RS at new high (~1 = leadership tell)

    return feats
