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


def decile_lift(scores, forward_returns, n_deciles: int = 10) -> dict:
    """Mean forward return by score decile, top-vs-bottom spread, top-decile hit rate,
    and monotonicity (rank correlation of decile index vs mean return)."""
    scores = np.asarray(scores, float)
    fwd = np.asarray(forward_returns, float)
    mask = ~(np.isnan(scores) | np.isnan(fwd))
    scores, fwd = scores[mask], fwd[mask]
    n = len(scores)
    ranks = scores.argsort().argsort()
    dec = np.clip(ranks * n_deciles // n, 0, n_deciles - 1)
    means = np.array([fwd[dec == d].mean() if (dec == d).any() else np.nan
                      for d in range(n_deciles)])
    hit = np.array([(fwd[dec == d] > 0).mean() if (dec == d).any() else np.nan
                    for d in range(n_deciles)])
    mono = spearmanr(np.arange(n_deciles), means).statistic
    return {
        "decile_mean": means.tolist(),
        "top_mean": float(means[-1]),
        "bottom_mean": float(means[0]),
        "spread": float(means[-1] - means[0]),
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
