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
