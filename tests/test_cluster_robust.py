"""C-1 unit tests: cluster-robust inference + the labeling dedup guard."""
import types

import numpy as np
import pytest

from gws.common.stats import cluster_robust_ttest
from gws.phase_a1.labeling import build_setup_labels


def test_univariate_screen_requires_clusters_on_discovery_path():
    import pandas as pd
    from gws.phase_a3.univariate import univariate_screen
    fm = pd.DataFrame({"f": np.arange(20.0)})
    y = np.array([0, 1] * 10)
    with pytest.raises(ValueError, match="cluster_ids is required"):
        univariate_screen(fm, y)                            # M-3: fail-closed without clusters
    univariate_screen(fm, y, iid_ok=True)                   # explicit escape hatch is allowed


def test_coef_recovers_difference_in_means():
    rng = np.random.default_rng(0)
    x = np.concatenate([rng.normal(1.0, 0.1, 200), rng.normal(0.0, 0.1, 200)])
    g = np.array([1] * 200 + [0] * 200, float)
    cl = np.arange(400)                       # each row its own cluster -> ~ OLS
    coef, p = cluster_robust_ttest(x, g, cl)
    assert abs(coef - 1.0) < 0.1
    assert p < 1e-6


def test_clustered_p_ignores_within_cluster_replication():
    # The C-1 mechanism: duplicating each cluster's rows N-fold inflates naive N (and shrinks a
    # naive SE toward 0), but adds no real information. A cluster-robust p must be ~unchanged by
    # replication — this is precisely what stops overlapping multi-scale moves from manufacturing
    # significance.
    rng = np.random.default_rng(0)
    K = 12
    g_c = np.array([1] * 6 + [0] * 6, float)
    val = 0.4 * g_c + rng.normal(0.0, 1.0, K)      # big between-cluster spread vs a 0.4 effect

    def build(n):
        x = np.concatenate([np.full(n, val[c]) for c in range(K)])
        g = np.concatenate([np.full(n, g_c[c]) for c in range(K)])
        cl = np.concatenate([np.full(n, c) for c in range(K)])
        return x, g, cl

    _, p_small = cluster_robust_ttest(*build(10))
    _, p_big = cluster_robust_ttest(*build(1000))
    assert abs(p_small - p_big) < 0.05             # 100x more rows -> same clustered verdict


def test_unestimable_returns_nan():
    x = np.arange(10, dtype=float)
    g = np.ones(10)                           # no group variance
    cl = np.arange(10)
    assert all(np.isnan(v) for v in cluster_robust_ttest(x, g, cl))


def _move(trough):
    return types.SimpleNamespace(trough_idx=trough)


def test_build_setup_labels_raises_on_duplicate_troughs():
    moves = {7: [_move(100), _move(100), _move(300)]}   # same trough at two scales
    with pytest.raises(ValueError, match="duplicate trough"):
        build_setup_labels(moves, n_days=500, forward_window_k=20)


def test_build_setup_labels_accepts_deduped_single_scale():
    moves = {7: [_move(260), _move(300)]}
    df = build_setup_labels(moves, n_days=500, forward_window_k=20)
    assert (df["label"].sum() > 0) and len(df) > 0
