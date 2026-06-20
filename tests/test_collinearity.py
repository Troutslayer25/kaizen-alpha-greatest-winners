import numpy as np
import pandas as pd

from gws.phase_a3.collinearity import (
    variance_inflation_factors, high_correlation_pairs, regime_collinearity,
)


def _frame(seed=0, n=400):
    rng = np.random.default_rng(seed)
    base = rng.normal(0, 1, n)
    return pd.DataFrame({
        "a": base,
        "a_dup": base + rng.normal(0, 0.01, n),   # near-duplicate of a
        "indep": rng.normal(0, 1, n),
    })


def test_vif_flags_duplicate():
    v = variance_inflation_factors(_frame())
    assert v["a"] > 10 and v["a_dup"] > 10        # the duplicate pair has severe VIF
    assert v["indep"] < 5                          # the independent column is fine


def test_high_correlation_pairs_finds_the_duplicate():
    pairs = high_correlation_pairs(_frame(), threshold=0.9)
    assert any({p["a"], p["b"]} == {"a", "a_dup"} for p in pairs)
    assert all({p["a"], p["b"]} != {"a", "indep"} for p in pairs)


def test_regime_collinearity_flags_feature_matching_regime():
    rng = np.random.default_rng(1)
    n = 400
    regime = rng.normal(0, 1, n)
    feats = pd.DataFrame({
        "looks_like_regime": regime + rng.normal(0, 0.05, n),   # near-collinear with regime
        "orthogonal": rng.normal(0, 1, n),
    })
    flagged = regime_collinearity(feats, regime, threshold=0.9)
    names = {f["feature"] for f in flagged}
    assert "looks_like_regime" in names
    assert "orthogonal" not in names
