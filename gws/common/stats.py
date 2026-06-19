"""Statistical helpers (provenance Tier A — framework-neutral).

Multiple-comparison correction, effect sizes, and ticker-block bootstrap. These
respect the study's correctness requirements (BH-FDR across all simultaneous tests;
effect sizes alongside p-values; ticker-level non-independence handled by resampling
whole tickers). NaN inputs (e.g. unestimable tests, warm-up feature values) are
excluded rather than silently corrupting the result.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import false_discovery_control


def benjamini_hochberg(pvals, alpha: float = 0.05):
    """Benjamini-Hochberg FDR via scipy. Returns (rejected: bool array, qvalues).

    NaN p-values (unestimable tests) are excluded from the procedure — they do not
    consume a rank position, so they cannot deflate the critical values of the valid
    tests. Their slots return rejected=False and qvalue=NaN.
    """
    p = np.asarray(pvals, float)
    n = len(p)
    rejected = np.zeros(n, bool)
    qvalues = np.full(n, np.nan)
    valid = ~np.isnan(p)
    if valid.sum() == 0:
        return rejected, qvalues
    q_v = false_discovery_control(p[valid], method="bh")
    qvalues[valid] = q_v
    rejected[valid] = q_v <= alpha
    return rejected, qvalues


def cohens_d(a, b) -> float:
    """Cohen's d (pooled SD). Positive when mean(a) > mean(b).

    Returns NaN when the effect is unestimable (n<2 in either arm, or zero pooled
    variance) — distinct from a measured zero effect.
    """
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sp2 = ((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2)
    sp = np.sqrt(sp2)
    return float((a.mean() - b.mean()) / sp) if sp > 0 else float("nan")


def block_bootstrap_by_ticker(values, tickers, stat_fn=np.mean, n_boot: int = 1000,
                              seed: int = 0, ci: float = 0.95):
    """Bootstrap a statistic by resampling whole tickers (block bootstrap).

    Returns (point_estimate, (lo, hi)). Resampling entire tickers preserves
    within-ticker dependence, so the CI is not artificially narrow. NaN values are
    dropped first. Group indices are built once via a single sort (O(n log n)),
    not a per-ticker scan.
    """
    values = np.asarray(values, float)
    tickers = np.asarray(tickers)
    mask = ~np.isnan(values)
    values, tickers = values[mask], tickers[mask]
    if values.size == 0:
        return float("nan"), (float("nan"), float("nan"))

    order = np.argsort(tickers, kind="stable")
    sorted_tk = tickers[order]
    uniq, starts = np.unique(sorted_tk, return_index=True)
    groups = np.split(order, starts[1:])
    n_groups = len(uniq)

    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot, float)
    for i in range(n_boot):
        chosen = rng.integers(0, n_groups, n_groups)
        idx = np.concatenate([groups[c] for c in chosen])
        boot[i] = stat_fn(values[idx])

    lo = float(np.quantile(boot, (1 - ci) / 2))
    hi = float(np.quantile(boot, 1 - (1 - ci) / 2))
    return float(stat_fn(values)), (lo, hi)
