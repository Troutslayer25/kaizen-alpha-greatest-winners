"""Empirical move clustering + mandatory bootstrap stability (Phase A1).

The study does not pre-specify how many move types exist. Clustering runs on the
post-hoc move-characterization dimensions (magnitude, duration, smoothness — all
legitimately computed from completed moves) and its stability is verified by
bootstrap resampling BEFORE any cluster structure is used downstream:

  mean ARI > 0.8        -> stable    (proceed with discrete clusters)
  0.6 <= mean ARI <= 0.8 -> marginal  (proceed with caution; flag boundary sensitivity)
  mean ARI < 0.6        -> unstable  (do NOT force clusters; use continuous-spectrum bands)

A degenerate result (fewer than 2 non-noise clusters) is reported as 'no_structure'
— the continuous-spectrum alternative applies there too.

HDBSCAN is the primary clusterer (it discovers the cluster count and isolates noise);
KMeans is available for the comparative input-set runs (T4). The clusterer is passed
in as a callable so the stability machinery is algorithm-agnostic.
"""
from __future__ import annotations

import numpy as np
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.metrics import adjusted_rand_score, mutual_info_score


def zscore(X) -> np.ndarray:
    X = np.asarray(X, float)
    return (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-12)


def _entropy(labels) -> float:
    _, counts = np.unique(labels, return_counts=True)
    p = counts / counts.sum()
    return float(-(p * np.log(p)).sum())


def variation_of_information(a, b) -> float:
    """VI(a,b) = H(a) + H(b) - 2 I(a;b), in nats. 0 = identical partitions."""
    return _entropy(a) + _entropy(b) - 2.0 * float(mutual_info_score(a, b))


def make_kmeans(k: int, seed: int = 0):
    return lambda X: KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(X)


def make_hdbscan(min_cluster_size: int = 15):
    return lambda X: HDBSCAN(min_cluster_size=min_cluster_size, copy=True).fit_predict(X)


def cluster_stability(X, clusterer, n_boot: int = 50, seed: int = 0) -> dict:
    """Bootstrap stability of a clustering. Returns the verdict dict written to
    gws.cluster_stability. `clusterer` maps an (n, d) array to integer labels
    (HDBSCAN uses -1 for noise)."""
    X = np.asarray(X, float)
    base = clusterer(X)
    n_clusters = len(set(np.unique(base)) - {-1})
    rng = np.random.default_rng(seed)
    aris, vis = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, len(X), len(X))           # bootstrap resample with replacement
        lab = clusterer(X[idx])
        uniq, first = np.unique(idx, return_index=True)  # compare on points present in both
        a, b = base[uniq], lab[first]
        aris.append(adjusted_rand_score(a, b))
        vis.append(variation_of_information(a, b))
    mean_ari = float(np.mean(aris))
    mean_vi = float(np.mean(vis))
    if n_clusters < 2:
        verdict = "no_structure"
    elif mean_ari > 0.8:
        verdict = "stable"
    elif mean_ari >= 0.6:
        verdict = "marginal"
    else:
        verdict = "unstable"
    return {
        "mean_adj_rand_index": mean_ari,
        "mean_variation_info": mean_vi,
        "n_clusters": n_clusters,
        "n_bootstrap_samples": n_boot,
        "stability_verdict": verdict,
    }


def resolve_representation(X, clusterer, labels, *, n_quantile_bands: int = 10,
                          n_boot: int = 50, seed: int = 0) -> dict:
    """Programmatically choose discrete-clusters vs continuous-quantile-bands for a
    MARGINAL stability result — removing the last human judgment call (critique keeper).

    A 'stable' verdict uses discrete clusters; 'unstable'/'no_structure' uses the
    continuous-spectrum fallback. For the ambiguous 'marginal' band (ARI 0.6-0.8), this
    scores both representations on within-group dispersion of the FIRST clustering input
    dimension (lower mean within-group variance = the cleaner partition of the data) and
    selects the lower-variance one. The math decides, not the analyst.

    Returns {representation: 'discrete'|'continuous', verdict, discrete_var, continuous_var}.
    Uses ARI thresholds via cluster_stability; no new tunable cutoff is introduced.
    """
    X = np.asarray(X, float)
    stab = cluster_stability(X, clusterer, n_boot=n_boot, seed=seed)
    verdict = stab["stability_verdict"]
    if verdict == "stable":
        return {"representation": "discrete", "verdict": verdict,
                "discrete_var": None, "continuous_var": None}
    if verdict in ("unstable", "no_structure"):
        return {"representation": "continuous", "verdict": verdict,
                "discrete_var": None, "continuous_var": None}

    # marginal -> tie-break on within-group dispersion of dimension 0
    dim0 = X[:, 0]
    discrete_var = _mean_within_group_var(dim0, labels)
    q = np.clip((dim0.argsort().argsort() * n_quantile_bands) // len(dim0),
                0, n_quantile_bands - 1)
    continuous_var = _mean_within_group_var(dim0, q)
    rep = "discrete" if discrete_var <= continuous_var else "continuous"
    return {"representation": rep, "verdict": verdict,
            "discrete_var": float(discrete_var), "continuous_var": float(continuous_var)}


def _mean_within_group_var(values, groups) -> float:
    values = np.asarray(values, float)
    groups = np.asarray(groups)
    vs = [values[groups == g].var() for g in np.unique(groups) if g != -1 and (groups == g).sum() > 1]
    return float(np.mean(vs)) if vs else float("inf")


def segment_by_early_drama(labels, had_early_shakeout) -> np.ndarray:
    """Split each (cluster or quantile-band) label into early-shakeout vs immediate-ascender
    sub-labels (critique keeper). Used with the continuous-spectrum fallback so distinct
    behavioral subsets (panic-then-rally vs calm grind) are not forced onto a generic
    magnitude/smoothness band. `had_early_shakeout` is a boolean per move (e.g. drawdown_timing
    in the early third AND mae above a small floor); the detector stays neutral — this only
    organizes already-detected moves. Returns string sub-labels '<label>|shakeout' / '|ascent'.
    """
    labels = np.asarray(labels)
    flag = np.asarray(had_early_shakeout, bool)
    return np.array([f"{lab}|{'shakeout' if f else 'ascent'}" for lab, f in zip(labels, flag)])
