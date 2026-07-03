"""Compute: vectorized rolling families are numerically identical to the per-point functions."""
import numpy as np

from gws.phase_a2.features_price_volume import compute_features
from gws.phase_a2.features_vectorized import VECTORIZED_FIELDS, compute_features_vectorized
from gws.validation.feature_equality import assert_vectorized_matches_pointwise


def _series(seed=0, n=600):
    rng = np.random.default_rng(seed)
    return np.abs(100 * np.cumprod(1 + rng.normal(0, 0.012, n)))


def test_vectorized_matches_pointwise_on_the_proven_families():
    close = _series()
    high, low, vol = close * 1.01, close * 0.99, np.full(len(close), 1e6)
    vec = compute_features_vectorized(close)

    def point_fn(i):
        return compute_features(close, high, low, vol, i)

    # sample across warm-up and steady-state indices
    idxs = list(range(0, len(close), 7))
    assert assert_vectorized_matches_pointwise(vec, point_fn, idxs)


def test_vectorized_covers_the_declared_fields():
    close = _series(1)
    vec = compute_features_vectorized(close)
    for fam in VECTORIZED_FIELDS:
        assert any(k.startswith(fam) for k in vec), f"{fam} missing from vectorized output"


def test_gate_catches_a_deliberately_wrong_vectorization():
    close = _series(2)
    high, low, vol = close * 1.01, close * 0.99, np.full(len(close), 1e6)
    vec = compute_features_vectorized(close)
    vec["dist_from_high_21"] = vec["dist_from_high_21"] + 0.01     # corrupt one family
    import pytest
    with pytest.raises(AssertionError):
        assert_vectorized_matches_pointwise(vec, lambda i: compute_features(close, high, low, vol, i),
                                            list(range(300, 400, 5)))
