import numpy as np

from gws.phase_a1.clustering import (
    zscore, variation_of_information, cluster_stability, make_kmeans, make_hdbscan,
    resolve_representation,
)


def _blobs(seed=0):
    rng = np.random.default_rng(seed)
    b1 = rng.normal([0, 0, 0], 0.3, (120, 3))
    b2 = rng.normal([6, 6, 0], 0.3, (120, 3))
    b3 = rng.normal([0, 6, 6], 0.3, (120, 3))
    return np.vstack([b1, b2, b3])


def test_zscore_unit_scale():
    X = np.array([[1.0, 100.0], [2.0, 200.0], [3.0, 300.0]])
    Z = zscore(X)
    assert np.allclose(Z.mean(axis=0), 0, atol=1e-9)
    assert np.allclose(Z.std(axis=0), 1, atol=1e-6)


def test_vi_identical_partitions_is_zero():
    a = np.array([0, 0, 1, 1, 2, 2])
    assert variation_of_information(a, a) == 0.0


def test_well_separated_blobs_are_stable():
    X = _blobs()
    res = cluster_stability(X, make_kmeans(3, seed=0), n_boot=30, seed=1)
    assert res["stability_verdict"] == "stable"
    assert res["mean_adj_rand_index"] > 0.8
    assert res["n_clusters"] == 3


def test_uniform_noise_is_not_stable():
    rng = np.random.default_rng(2)
    X = rng.uniform(0, 5, (300, 3))
    res = cluster_stability(X, make_kmeans(3, seed=0), n_boot=30, seed=1)
    # forcing k=3 on structureless data is unstable under resampling
    assert res["mean_adj_rand_index"] < 0.8
    assert res["stability_verdict"] in ("unstable", "marginal")


def test_hdbscan_discovers_blob_count():
    X = _blobs()
    labels = make_hdbscan(min_cluster_size=15)(X)
    n_clusters = len(set(np.unique(labels)) - {-1})
    assert n_clusters >= 2          # discovers the blob structure without being told k


def test_resolve_representation_stable_uses_discrete():
    X = _blobs()
    labels = make_kmeans(3, seed=0)(X)
    r = resolve_representation(X, make_kmeans(3, seed=0), labels, n_boot=20, seed=1)
    assert r["representation"] == "discrete"   # well-separated -> discrete clusters


def test_resolve_representation_structureless_uses_continuous():
    rng = np.random.default_rng(5)
    X = rng.uniform(0, 5, (300, 3))
    labels = make_kmeans(3, seed=0)(X)
    r = resolve_representation(X, make_kmeans(3, seed=0), labels, n_boot=20, seed=1)
    # forced clusters on noise are unstable -> continuous fallback, no human call
    assert r["representation"] == "continuous"


def test_resolve_representation_marginal_is_decided_by_math():
    # A marginal case must still yield a deterministic representation with a recorded
    # variance comparison, never an undecided/None.
    rng = np.random.default_rng(7)
    # mildly separated blobs -> tends to land in the marginal ARI band
    X = np.vstack([rng.normal([0, 0, 0], 1.2, (150, 3)),
                   rng.normal([2.5, 2.5, 0], 1.2, (150, 3))])
    labels = make_kmeans(2, seed=0)(X)
    r = resolve_representation(X, make_kmeans(2, seed=0), labels, n_boot=20, seed=1)
    assert r["representation"] in ("discrete", "continuous")
    if r["verdict"] == "marginal":
        assert r["discrete_var"] is not None and r["continuous_var"] is not None
