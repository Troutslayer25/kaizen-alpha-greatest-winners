"""Statistical helpers (provenance Tier A — framework-neutral).

Multiple-comparison correction, effect sizes, and ticker-block bootstrap. These
respect the study's correctness requirements (BH-FDR across all simultaneous tests;
effect sizes alongside p-values; ticker-level non-independence handled by resampling
whole tickers). NaN inputs (e.g. unestimable tests, warm-up feature values) are
excluded rather than silently corrupting the result.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import false_discovery_control, t as _tdist


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


def cluster_robust_ttest(x, group, cluster):
    """Two-sample / slope test with CLUSTER-ROBUST standard errors (review C-1).

    Regresses x on [1, group] and returns (coef, pvalue) for `group`, where the SE clusters
    on `cluster` (CR1 finite-sample correction, dof = n_clusters - 1). This replaces naive
    i.i.d. tests on the discovery path: with overlapping multi-scale moves and 5-day-cadence
    labels sharing K-day windows, rows within a ticker are dependent and pooled p-values are
    anti-conservative (§13 risk #9). `group` may be a 0/1 setup indicator (coef = difference
    in means) or continuous (coef = slope). NaN x are dropped. Returns (nan, nan) when
    unestimable (fewer than 2 clusters, no group variance, singular design)."""
    x = np.asarray(x, float)
    g = np.asarray(group, float)
    cl = np.asarray(cluster)
    m = ~(np.isnan(x) | np.isnan(g))
    x, g, cl = x[m], g[m], cl[m]
    n = x.size
    _, cl_idx = np.unique(cl, return_inverse=True)
    G = int(cl_idx.max()) + 1 if n else 0
    if n < 3 or G < 2 or g.min() == g.max():
        return float("nan"), float("nan")

    X = np.column_stack([np.ones(n), g])
    XtX = X.T @ X
    try:
        XtX_inv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        return float("nan"), float("nan")
    beta = XtX_inv @ (X.T @ x)
    u = x - X @ beta
    score = X * u[:, None]                       # n x 2 per-observation score
    S = np.zeros((G, 2))
    np.add.at(S, cl_idx, score)                  # sum scores within cluster (O(n))
    meat = S.T @ S
    c = (G / (G - 1)) * ((n - 1) / (n - 2))      # CR1 correction, k=2 params
    V = c * (XtX_inv @ meat @ XtX_inv)
    se = float(np.sqrt(V[1, 1])) if V[1, 1] > 0 else float("nan")
    if not np.isfinite(se) or se <= 0:
        return float(beta[1]), float("nan")
    tstat = beta[1] / se
    p = 2.0 * _tdist.sf(abs(tstat), df=G - 1)
    return float(beta[1]), float(p)


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


def ticker_multiplier_bootstrap(values, tickers, *, n_boot: int = 1000, seed: int = 0,
                                ci: float = 0.95):
    """Ticker-block bootstrap of the MEAN for MANY columns at once (review, compute aspect).

    `values` is (n, k) — one column per feature. Each replicate draws a single vector of
    ticker resample-counts (multinomial) and reuses it across all k columns as weights, so the
    whole thing is ~n_boot weighted reductions over an (n, k) matrix instead of k separate
    index-concatenating loops (memory-bandwidth-infeasible at k=500). Returns (point[k],
    lo[k], hi[k]) — per-column point estimate and clustered CI."""
    V = np.asarray(values, float)
    if V.ndim == 1:
        V = V[:, None]
    tickers = np.asarray(tickers)
    _, group_idx = np.unique(tickers, return_inverse=True)
    G = int(group_idx.max()) + 1
    n, k = V.shape

    rng = np.random.default_rng(seed)
    boot = np.empty((n_boot, k))
    uniform = np.full(G, 1.0 / G)
    for b in range(n_boot):
        counts = rng.multinomial(G, uniform)          # resample G tickers with replacement
        w = counts[group_idx].astype(float)           # per-row weight (shared across columns)
        wsum = w.sum()
        boot[b] = (w @ V) / wsum if wsum > 0 else np.nan
    lo = np.quantile(boot, (1 - ci) / 2, axis=0)
    hi = np.quantile(boot, 1 - (1 - ci) / 2, axis=0)
    point = V.mean(axis=0)
    return point, lo, hi
