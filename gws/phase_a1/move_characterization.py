"""Comprehensive move characterization (Phase A1) — the classification substrate.

The study's second goal (beyond edge discovery) is to CLASSIFY every detected move richly enough
that the database answers questions not yet imagined. The detector (move_detector_mfe) records the
minimal path-shape set it needs; this module computes the FULL descriptor vector for each move so
`gws.moves` becomes a queryable catalog: magnitude/time, path shape, pullback structure, streaks,
gaps, volume profile, the pre-move base, and relative strength.

These describe the move — a post-hoc OUTCOME (trough..peak is future-derived). They are for
CLASSIFICATION / clustering / ad-hoc query ONLY, never setup features; the quarantine audit
(gws.validation.quarantine) enforces that separation. Descriptors are deliberately additive: add a
field here + a column in gws.moves and every past move can be re-characterized — no re-detection.

    from gws.phase_a1.move_characterization import characterize_move, DESCRIPTOR_FIELDS
    row = characterize_move(move, close, high, low, volume=vol, bench_close=bench)
"""
from __future__ import annotations

import numpy as np

# Pre-committed characterization parameters (freeze in the A1 spec before real data).
PULLBACK_THRESHOLD = 0.05      # a from-peak dip beyond this counts as a distinct pullback
GAP_THRESHOLD = 0.05           # |overnight return| beyond this counts as a gap
BASE_WINDOW = 63               # trading days before the trough used to characterize the pre-move base

DESCRIPTOR_FIELDS = (
    # magnitude / time
    "magnitude", "log_magnitude", "duration_days", "velocity", "annualized_return",
    # path shape
    "smoothness", "early_smoothness", "late_smoothness", "mae", "max_intra_drawdown",
    "drawdown_timing",
    # pullback structure
    "num_pullbacks", "largest_pullback", "mean_pullback",
    # daily-return structure
    "up_day_share", "max_up_streak", "max_down_streak", "return_skew", "front_loaded_ratio",
    # during-move MA interaction (how the move rode / respected moving averages)
    "pct_days_above_sma50", "pct_days_above_sma200", "first_close_below_sma50_frac",
    # big-up/down days (close-to-close; NOT true overnight gaps — see note)
    "big_day_count", "largest_big_day",
    # volume profile
    "vol_expansion", "up_down_vol_ratio", "vol_trend",
    # relative strength
    "rs_move", "rs_at_peak_is_high",
)   # NOTE: the pre-move base descriptors are PIT (data <= trough) and therefore live in the
    # INCEPTION bag (incept_base_depth_63 / incept_base_return_63), not here (review F1b) — so the
    # descriptor/inception split equals the outcome/PIT split exactly and the quarantine is honest.


def _smoothness(seg):
    net = seg[-1] - seg[0]
    path = float(np.abs(np.diff(seg)).sum())
    return float(net / path) if path > 0 else 0.0


def _streaks(rets):
    up = dn = max_up = max_dn = 0
    for r in rets:
        if r > 0:
            up += 1; dn = 0; max_up = max(max_up, up)
        elif r < 0:
            dn += 1; up = 0; max_dn = max(max_dn, dn)
        else:
            up = dn = 0
    return max_up, max_dn


def _pullbacks(seg, threshold, recovery: float = 0.5):
    """Count/size of DISTINCT from-running-peak retracements exceeding `threshold`, with recovery
    hysteresis (review quant M): a pullback only completes once drawdown recedes below
    `threshold*recovery`, so chattering across the threshold counts as ONE pullback, not three."""
    running = np.maximum.accumulate(seg)
    dd = np.where(running > 0, (running - seg) / running, 0.0)
    exit_level = threshold * recovery
    depths, in_pb, trough = [], False, 0.0
    for d in dd:
        if not in_pb:
            if d > threshold:
                in_pb = True; trough = d
        else:
            trough = max(trough, d)
            if d < exit_level:
                depths.append(trough); in_pb = False; trough = 0.0
    if in_pb:
        depths.append(trough)
    if not depths:
        return 0, 0.0, 0.0
    return len(depths), float(max(depths)), float(np.mean(depths))


def characterize_move(move, close, high=None, low=None, volume=None, bench_close=None, *,
                      pullback_threshold: float = PULLBACK_THRESHOLD,
                      gap_threshold: float = GAP_THRESHOLD, base_window: int = BASE_WINDOW) -> dict:
    """Return the full descriptor dict for one detected move. `move` needs .trough_idx/.peak_idx.
    Optional high/low/volume/bench_close enable the gap, volume, and relative-strength families
    (fields they need are NaN when the input is absent)."""
    close = np.asarray(close, float)
    ti, pi = int(move.trough_idx), int(move.peak_idx)
    seg = close[ti:pi + 1]
    s, pk = seg[0], seg[-1]
    n = len(seg)
    rets = np.diff(seg) / seg[:-1] if n > 1 else np.array([0.0])

    running = np.maximum.accumulate(seg)
    dd = np.where(running > 0, (running - seg) / running, 0.0)
    third = max(2, n // 3)
    npb, largest_pb, mean_pb = _pullbacks(seg, pullback_threshold)
    max_up, max_dn = _streaks(rets)
    half = max(1, n // 2)
    first_half_gain = seg[half] / s - 1.0 if s > 0 else np.nan
    total_gain = pk / s - 1.0 if s > 0 else np.nan

    # front-loaded ratio guarded + clipped: undefined for tiny total moves and bounded to [-1, 2]
    # so a 0.4%-gain move can't produce a -2.5 outlier (review quant M).
    fl = (first_half_gain / total_gain) if (total_gain == total_gain and abs(total_gain) > 0.05) else np.nan
    fl = float(np.clip(fl, -1.0, 2.0)) if fl == fl else np.nan
    # annualized_return capped: a 5-day double annualizes to ~1e15 and dominates any scale — cap
    # to a sane ceiling (it stays useful as a bounded velocity proxy; magnitude/duration carry the
    # raw info and clustering selects among these collinear encodings, it does not use them raw).
    ann = float(min((pk / s) ** (252.0 / max(1, pi - ti)) - 1.0, 1e4)) if s > 0 else np.nan

    d = {
        "magnitude": float(total_gain),
        "log_magnitude": float(np.log(pk / s)) if s > 0 and pk > 0 else np.nan,
        "duration_days": int(pi - ti),
        "velocity": float(total_gain / max(1, pi - ti)),
        "annualized_return": ann,
        "smoothness": _smoothness(seg),
        "early_smoothness": _smoothness(seg[:third]),
        "late_smoothness": _smoothness(seg[-third:]),
        "mae": float(max(0.0, (s - seg.min()) / s)) if s > 0 else np.nan,
        "max_intra_drawdown": float(dd.max()),
        "drawdown_timing": float(np.argmax(dd) / (n - 1)) if n > 1 and dd.max() > 0 else 0.0,
        "num_pullbacks": int(npb),
        "largest_pullback": largest_pb,
        "mean_pullback": mean_pb,
        "up_day_share": float(np.mean(rets > 0)),
        "max_up_streak": int(max_up),
        "max_down_streak": int(max_dn),
        "return_skew": float(_skew(rets)),
        "front_loaded_ratio": fl,
        "big_day_count": np.nan, "largest_big_day": np.nan,
        "vol_expansion": np.nan, "up_down_vol_ratio": np.nan, "vol_trend": np.nan,
        "rs_move": np.nan, "rs_at_peak_is_high": np.nan,
    }

    if n > 1:
        gaps = np.abs(rets)                             # close-to-close big days (NOT true gaps)
        d["big_day_count"] = int(np.sum(gaps > gap_threshold))
        d["largest_big_day"] = float(gaps.max())

    if volume is not None:
        volume = np.asarray(volume, float)
        vseg = volume[ti:pi + 1]
        base0 = max(0, ti - base_window)
        base_vol = volume[base0:ti]
        if base_vol.size and base_vol.mean() > 0:
            d["vol_expansion"] = float(vseg.mean() / base_vol.mean())
        if n > 1:
            up_v = vseg[1:][rets > 0].sum(); dn_v = vseg[1:][rets < 0].sum()
            d["up_down_vol_ratio"] = float(up_v / dn_v) if dn_v > 0 else np.nan
            if vseg.mean() > 0 and n > 2:
                d["vol_trend"] = float(np.polyfit(np.arange(n), vseg, 1)[0] / vseg.mean())

    if bench_close is not None:
        bench = np.asarray(bench_close, float)
        if bench[ti] > 0 and bench[pi] > 0 and s > 0:
            d["rs_move"] = float((pk / s) / (bench[pi] / bench[ti]) - 1.0)
            rs_line = np.where(bench[ti:pi + 1] > 0, seg / bench[ti:pi + 1], np.nan)
            if np.isfinite(rs_line).any():
                d["rs_at_peak_is_high"] = float(rs_line[-1] >= np.nanmax(rs_line))

    # during-move MA interaction (practitioner MC-1): what share of the move's days closed above
    # the 50/200-day SMA, and how far into the move (fraction) the first close BELOW the 50-day
    # occurred (1.0 = never broke it — a textbook trend-ride). Each day's MA uses close[:t+1] only.
    for p, key in ((50, "pct_days_above_sma50"), (200, "pct_days_above_sma200")):
        flags = [(close[t] > close[t - p + 1:t + 1].mean()) for t in range(ti, pi + 1) if t - p + 1 >= 0]
        d[key] = float(np.mean(flags)) if flags else np.nan
    below = [(t - ti) / max(1, n - 1) for t in range(ti, pi + 1)
             if t - 49 >= 0 and close[t] < close[t - 49:t + 1].mean()]
    d["first_close_below_sma50_frac"] = float(below[0]) if below else 1.0
    return d


def _skew(x):
    x = np.asarray(x, float)
    if x.size < 3 or x.std() == 0:
        return 0.0
    return float(np.mean(((x - x.mean()) / x.std()) ** 3))


# ---------------------------------------------------------------------------
# Inception context — PIT state AT THE TROUGH (only close[:trough+1] etc.)
# ---------------------------------------------------------------------------
# So a move can later be queried by what the tape looked like when it BEGAN — "moves that
# started above the 200-day MA", "moves whose RSI was oversold at the trough", "moves leading
# the benchmark at inception". These are measured strictly at/<=the trough, so they are
# forward-invariant (bias-free) and can be stored on the move row and filtered directly. This is
# DISTINCT from the outcome descriptors above (which are post-hoc). Future-invariance is
# unit-tested (tests/test_move_characterization.py).

INCEPTION_MA_PERIODS = (20, 50, 150, 200)
INCEPTION_FIELDS = tuple(f"incept_price_to_sma{p}" for p in INCEPTION_MA_PERIODS) + (
    "incept_price_to_ema8", "incept_price_to_ema21", "incept_sma50_slope_21",
    "incept_above_sma200", "incept_dist_from_high_252", "incept_dist_from_low_252",
    "incept_atr_pct_14", "incept_rsi_14", "incept_vol_vs_avg_50", "incept_rs_vs_bench_63",
    "incept_base_depth_63", "incept_base_return_63",
)


def _sma_rel(close, i, p):
    if i - p + 1 < 0:
        return np.nan
    w = close[i - p + 1:i + 1]
    m = w.mean()
    return float(close[i] / m - 1.0) if m > 0 else np.nan


def _ema_rel(close, i, p):
    from gws.common.indicators import ema
    if i - p + 1 < 0:
        return np.nan
    e = ema(close[:i + 1], p)[-1]                        # causal: EMA recursion uses only <= i
    return float(close[i] / e - 1.0) if e == e and e > 0 else np.nan


def _wilder_rsi(close, i, p=14):
    """Wilder-smoothed RSI at index i (matches every charting platform), causal on close[:i+1]."""
    if i - p < 0:
        return np.nan
    d = np.diff(close[:i + 1])
    gains = np.where(d > 0, d, 0.0)
    losses = np.where(d < 0, -d, 0.0)
    avg_g, avg_l = gains[:p].mean(), losses[:p].mean()
    for k in range(p, len(d)):
        avg_g = (avg_g * (p - 1) + gains[k]) / p
        avg_l = (avg_l * (p - 1) + losses[k]) / p
    if avg_l == 0:
        return 100.0 if avg_g > 0 else 50.0
    return float(100.0 - 100.0 / (1.0 + avg_g / avg_l))


def inception_context(move, close, high=None, low=None, volume=None, bench_close=None) -> dict:
    """PIT descriptors of the tape AT the move's trough (uses only data <= trough).
    Forward-invariant by construction — safe to store on the move row and query against."""
    close = np.asarray(close, float)
    i = int(move.trough_idx)
    out = {f"incept_price_to_sma{p}": _sma_rel(close, i, p) for p in INCEPTION_MA_PERIODS}
    out["incept_price_to_ema8"] = _ema_rel(close, i, 8)
    out["incept_price_to_ema21"] = _ema_rel(close, i, 21)
    # 50-day SMA slope over the last 21 bars, normalized by price (rising-MA trend-template test)
    if i - 70 >= 0:
        s50_now = close[i - 49:i + 1].mean()
        s50_prior = close[i - 70:i - 20].mean()
        out["incept_sma50_slope_21"] = float((s50_now - s50_prior) / close[i]) if close[i] > 0 else np.nan
    else:
        out["incept_sma50_slope_21"] = np.nan
    sma200 = _sma_rel(close, i, 200)
    out["incept_above_sma200"] = float(sma200 > 0) if sma200 == sma200 else np.nan
    if i - 251 >= 0:
        w = close[i - 251:i + 1]
        mx, mn = w.max(), w.min()
        out["incept_dist_from_high_252"] = float(close[i] / mx - 1.0) if mx > 0 else np.nan
        out["incept_dist_from_low_252"] = float(close[i] / mn - 1.0) if mn > 0 else np.nan
    else:
        out["incept_dist_from_high_252"] = out["incept_dist_from_low_252"] = np.nan
    if high is not None and low is not None and i - 14 >= 0:
        from gws.common.indicators import wilder_atr
        atr = wilder_atr(np.asarray(high, float)[:i + 1], np.asarray(low, float)[:i + 1],
                         close[:i + 1], 14)
        out["incept_atr_pct_14"] = float(atr[-1] / close[i]) if close[i] > 0 else np.nan
    else:
        out["incept_atr_pct_14"] = np.nan
    out["incept_rsi_14"] = _wilder_rsi(close, i, 14)
    # prior 50-day average volume (excludes the trough day — conventional)
    if volume is not None and i - 50 >= 0:
        v = np.asarray(volume, float)
        avg = v[i - 50:i].mean()
        out["incept_vol_vs_avg_50"] = float(v[i] / avg) if avg > 0 else np.nan
    else:
        out["incept_vol_vs_avg_50"] = np.nan
    if bench_close is not None and i - 63 >= 0:
        b = np.asarray(bench_close, float)
        if close[i - 63] > 0 and b[i] > 0 and b[i - 63] > 0:
            out["incept_rs_vs_bench_63"] = float((close[i] / close[i - 63]) / (b[i] / b[i - 63]) - 1.0)
        else:
            out["incept_rs_vs_bench_63"] = np.nan
    else:
        out["incept_rs_vs_bench_63"] = np.nan
    # pre-move base (PIT — data <= trough): depth of the decline into the trough and the base's
    # own return. Relocated here from the descriptor bag so the outcome/PIT split is exact (F1b).
    base0 = max(0, i - 63)
    base_seg = close[base0:i + 1]
    if base_seg.size > 1:
        bmax = base_seg.max()
        out["incept_base_depth_63"] = float((bmax - close[i]) / bmax) if bmax > 0 else np.nan
        out["incept_base_return_63"] = float(close[i] / base_seg[0] - 1.0) if base_seg[0] > 0 else np.nan
    else:
        out["incept_base_depth_63"] = out["incept_base_return_63"] = np.nan
    return out
