"""Scoring backtest: decile lift + capacity diagnostic (Part X / Phase B2).

Decile lift answers "do high-scoring stocks subsequently produce larger forward
moves, monotonically?". The capacity diagnostic answers "is the top decile actually
tradeable at institutional size, or is it thin micro-caps?" — a model whose edge
lives only in untradeable names has limited practical value regardless of statistics.

Forward-return computation and the holding/measurement convention are the caller's
responsibility (exit logic is out of scope); this operates on already-computed
forward returns aligned to the scored observations.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr


def _deciles(scores, n_deciles):
    n = len(scores)
    ranks = scores.argsort().argsort()
    return np.clip(ranks * n_deciles // n, 0, n_deciles - 1)


def decile_lift(scores, forward_returns, n_deciles: int = 10, *, dates=None) -> dict:
    """Mean forward return by score decile, top-vs-bottom spread, top-decile hit rate,
    and monotonicity (rank correlation of decile index vs mean return).

    `dates` (review M-7): when supplied, deciles are formed WITHIN each date and the decile
    means are averaged across dates, so the lift measures cross-sectional SELECTION rather than
    regime TIMING (a pooled decile concentrates the top bin in particular eras when base rates
    drift). The spread also gets a date-clustered CI (mean +/- 1.96*SE across dates)."""
    scores = np.asarray(scores, float)
    fwd = np.asarray(forward_returns, float)
    mask = ~(np.isnan(scores) | np.isnan(fwd))
    scores, fwd = scores[mask], fwd[mask]
    dts = None if dates is None else np.asarray(dates)[mask]

    if dts is None:
        dec = _deciles(scores, n_deciles)
        means = np.array([fwd[dec == d].mean() if (dec == d).any() else np.nan
                          for d in range(n_deciles)])
        hit = np.array([(fwd[dec == d] > 0).mean() if (dec == d).any() else np.nan
                        for d in range(n_deciles)])
        spread_ci = None
    else:
        # per-date deciles, then average across dates
        per_date_means, per_date_hits, per_date_spread = [], [], []
        for d in np.unique(dts):
            m = dts == d
            if m.sum() < n_deciles:
                continue
            dec = _deciles(scores[m], n_deciles)
            fm = fwd[m]
            dm = np.array([fm[dec == k].mean() if (dec == k).any() else np.nan
                           for k in range(n_deciles)])
            dh = np.array([(fm[dec == k] > 0).mean() if (dec == k).any() else np.nan
                           for k in range(n_deciles)])
            per_date_means.append(dm); per_date_hits.append(dh)
            per_date_spread.append(dm[-1] - dm[0])
        means = np.nanmean(per_date_means, axis=0)
        hit = np.nanmean(per_date_hits, axis=0)
        sp = np.asarray(per_date_spread, float)
        se = float(np.nanstd(sp, ddof=1) / np.sqrt(len(sp))) if len(sp) > 1 else float("nan")
        spread_ci = [float(np.nanmean(sp) - 1.96 * se), float(np.nanmean(sp) + 1.96 * se)]

    mono = spearmanr(np.arange(n_deciles), means).statistic
    return {
        "decile_mean": means.tolist(),
        "top_mean": float(means[-1]),
        "bottom_mean": float(means[0]),
        "spread": float(means[-1] - means[0]),
        "spread_ci": spread_ci,
        "top_hit_rate": float(hit[-1]),
        "monotonicity": float(mono),
    }


def capacity_diagnostic(scores, adv_50d, *, top_frac: float = 0.1,
                        clip_pct: float = 0.01) -> dict:
    """For the top `top_frac` of scored names: median 50-day ADV, the per-name clip
    size that stays within `clip_pct` of ADV, and aggregate theoretical capacity."""
    scores = np.asarray(scores, float)
    adv = np.asarray(adv_50d, float)
    n = len(scores)
    k = max(1, int(n * top_frac))
    top_idx = np.argsort(scores)[-k:]
    top_adv = adv[top_idx]
    clip = clip_pct * top_adv
    return {
        "n_top": k,
        "median_adv": float(np.median(top_adv)),
        "median_clip_per_name": float(np.median(clip)),
        "aggregate_capacity": float(clip.sum()),
    }
