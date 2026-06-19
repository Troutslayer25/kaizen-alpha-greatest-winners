"""Statistical helpers (provenance Tier A — framework-neutral).

Multiple-comparison correction, effect sizes, and ticker-block bootstrap. These
respect the study's correctness requirements (BH-FDR across all simultaneous tests;
effect sizes alongside p-values; ticker-level non-independence handled by resampling
whole tickers).
"""
from __future__ import annotations

import numpy as np


def benjamini_hochberg(pvals, alpha: float = 0.05):
    """Benjamini-Hochberg FDR. Returns (rejected: bool array, qvalues: float array)."""
    p = np.asarray(pvals, float)
    n = len(p)
    if n == 0:
        return np.zeros(0, bool), np.zeros(0, float)
    order = np.argsort(p)
    ranked = p[order]
    ranks = np.arange(1, n + 1)

    crit = (ranks / n) * alpha
    passed = ranked <= crit
    rej_sorted = np.zeros(n, bool)
    if passed.any():
        kmax = np.max(np.where(passed)[0])
        rej_sorted[: kmax + 1] = True
    rejected = np.zeros(n, bool)
    rejected[order] = rej_sorted

    q_sorted = ranked * n / ranks
    q_sorted = np.minimum.accumulate(q_sorted[::-1])[::-1]
    qvalues = np.empty(n, float)
    qvalues[order] = np.clip(q_sorted, 0.0, 1.0)
    return rejected, qvalues


def cohens_d(a, b) -> float:
    """Cohen's d (pooled SD). Positive when mean(a) > mean(b)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    sp2 = ((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2)
    sp = np.sqrt(sp2)
    return float((a.mean() - b.mean()) / sp) if sp > 0 else 0.0


def block_bootstrap_by_ticker(values, tickers, stat_fn=np.mean, n_boot: int = 1000,
                              seed: int = 0, ci: float = 0.95):
    """Bootstrap a statistic by resampling whole tickers (block bootstrap).

    Returns (point_estimate, (lo, hi)). Resampling entire tickers preserves
    within-ticker dependence, so the CI is not artificially narrow.
    """
    values = np.asarray(values, float)
    tickers = np.asarray(tickers)
    uniq = np.unique(tickers)
    groups = {u: np.where(tickers == u)[0] for u in uniq}
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot, float)
    for i in range(n_boot):
        chosen = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([groups[c] for c in chosen])
        boot[i] = stat_fn(values[idx])
    lo = float(np.quantile(boot, (1 - ci) / 2))
    hi = float(np.quantile(boot, 1 - (1 - ci) / 2))
    return float(stat_fn(values)), (lo, hi)
