import numpy as np
import pandas as pd

from gws.phase_a1.matched_controls import build_matched_controls


def _pool(seed=0, n=500):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "ticker_id": rng.integers(0, 20, n),
        "as_of_index": rng.integers(0, 1000, n),
        "size_bucket": rng.integers(0, 3, n),
        "sector": rng.integers(0, 4, n),
    })


def test_controls_share_setup_buckets():
    pool = _pool()
    setups = pool.sample(10, random_state=1).reset_index(drop=True)
    controls, diag = build_matched_controls(
        setups, pool, ["size_bucket", "sector"], n_per_setup=2, exclude_same_ticker=False)
    assert len(controls) > 0
    for _, c in controls.iterrows():
        s = setups.loc[c["matched_setup_id"]]
        assert c["size_bucket"] == s["size_bucket"]
        assert c["sector"] == s["sector"]
    assert diag["mean_effective_pool"] > 0


def test_overmatching_shrinks_effective_pool():
    pool = _pool()
    setups = pool.sample(10, random_state=2).reset_index(drop=True)
    _, diag_min = build_matched_controls(setups, pool, ["size_bucket", "sector"], n_per_setup=1)
    _, diag_over = build_matched_controls(
        setups, pool, ["size_bucket", "sector", "as_of_index"], n_per_setup=1)
    # adding a near-unique match column collapses the available control pool
    assert diag_over["mean_effective_pool"] <= diag_min["mean_effective_pool"]
    assert diag_over["n_setups_with_empty_pool"] >= diag_min["n_setups_with_empty_pool"]
