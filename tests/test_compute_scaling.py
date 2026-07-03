"""Compute aspect: matrix VIF, SVC cap, multiplier-weight bootstrap, m-out-of-n stability."""
import numpy as np
import pandas as pd

from gws.common.stats import block_bootstrap_by_ticker, ticker_multiplier_bootstrap
from gws.phase_a1.clustering import cluster_stability, make_kmeans
from gws.phase_a3.collinearity import variance_inflation_factors
from gws.phase_a3.ml_bakeoff import _CappedSVC


def test_matrix_vif_matches_r2_definition():
    rng = np.random.default_rng(0)
    n = 500
    a = rng.normal(0, 1, n)
    df = pd.DataFrame({"a": a, "b": 0.7 * a + rng.normal(0, 0.5, n), "c": rng.normal(0, 1, n)})
    vif = variance_inflation_factors(df)
    # closed-form check for column 'a' via R^2 of a ~ b + c
    Z = df.to_numpy(float)
    A = np.column_stack([np.ones(n), Z[:, 1], Z[:, 2]])
    beta, *_ = np.linalg.lstsq(A, Z[:, 0], rcond=None)
    r2 = 1 - ((Z[:, 0] - A @ beta) ** 2).sum() / ((Z[:, 0] - Z[:, 0].mean()) ** 2).sum()
    assert abs(vif["a"] - 1 / (1 - r2)) < 0.05


def test_multiplier_bootstrap_recovers_mean_and_widens_under_clustering():
    rng = np.random.default_rng(2)
    G, per = 40, 50
    tickers = np.repeat(np.arange(G), per)
    # column 0: iid noise; column 1: strong ticker-level component (clustered)
    iid = rng.normal(0, 1, G * per)
    tk_mean = np.repeat(rng.normal(0, 1, G), per)
    clustered = tk_mean + rng.normal(0, 0.1, G * per)
    V = np.column_stack([iid, clustered])
    point, lo, hi = ticker_multiplier_bootstrap(V, tickers, n_boot=500)
    assert lo[0] < point[0] < hi[0]                     # CI brackets the point
    assert (hi[1] - lo[1]) > (hi[0] - lo[0])            # clustered column -> wider CI


def test_multiplier_bootstrap_matches_block_bootstrap_single_column():
    rng = np.random.default_rng(3)
    tickers = np.repeat(np.arange(30), 40)
    x = np.repeat(rng.normal(0, 1, 30), 40) + rng.normal(0, 0.2, 1200)
    _, (blo, bhi) = block_bootstrap_by_ticker(x, tickers, n_boot=800, seed=0)
    _, mlo, mhi = ticker_multiplier_bootstrap(x[:, None], tickers, n_boot=800, seed=0)
    assert abs(mlo[0] - blo) < 0.1 and abs(mhi[0] - bhi) < 0.1


def test_capped_svc_bounds_training_size():
    rng = np.random.default_rng(4)
    X = rng.normal(0, 1, (600, 3)); y = (X[:, 0] > 0).astype(int)
    m = _CappedSVC(cap=50).fit(X, y)
    assert m.n_train_ <= 50                             # trained on <= cap rows
    assert m.predict_proba(X).shape == (600, 2)


def test_cluster_stability_subsample_runs():
    rng = np.random.default_rng(5)
    X = np.concatenate([rng.normal(-5, 0.5, (80, 2)), rng.normal(5, 0.5, (80, 2))])
    out = cluster_stability(X, make_kmeans(2, seed=0), n_boot=10, subsample_frac=0.5)
    assert out["n_clusters"] == 2 and out["stability_verdict"] in {"stable", "marginal"}
