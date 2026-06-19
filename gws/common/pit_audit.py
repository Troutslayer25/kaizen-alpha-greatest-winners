"""Point-in-time self-audit harness.

The single highest-leverage correctness tool in the study: it mechanically proves
that a feature computed as of index `i` is INVARIANT to any change in the future
bars (indices > i). If a feature accidentally uses forward data, mutating the future
changes its value and the check fails. This catches look-ahead at its source rather
than relying on a reviewer to spot it.

Used in tests now (against synthetic data) and intended to run as a standing guard
over the real feature extraction in Phase A2.
"""
from __future__ import annotations

import numpy as np


def _equalish(a, b, tol=1e-9):
    if a is None or b is None:
        return a is b
    if isinstance(a, float) and (np.isnan(a) or np.isnan(b)):
        return np.isnan(a) and np.isnan(b)
    return abs(a - b) <= tol * (1 + abs(a))


def assert_future_invariant(compute_fn, series: dict, i, *, n_trials=5, seed=0, **kwargs):
    """Assert compute_fn(...at i...) does not depend on any bar after `i`.

    `compute_fn` is called as compute_fn(**series_at_i, i, **kwargs) where each value
    in `series` is a 1-D array passed by its keyword name. We compute the baseline,
    then repeatedly randomize every array beyond `i` and recompute; all feature values
    must be unchanged.

    Returns the baseline feature dict on success; raises AssertionError on leakage.
    """
    rng = np.random.default_rng(seed)
    base_arrays = {k: np.asarray(v, float) for k, v in series.items()}
    baseline = compute_fn(**base_arrays, i=i, **kwargs)

    n = len(next(iter(base_arrays.values())))
    for _ in range(n_trials):
        mutated = {}
        for k, v in base_arrays.items():
            m = v.copy()
            if i + 1 < n:
                m[i + 1 :] = m[i + 1 :] * rng.uniform(0.5, 1.5, size=n - i - 1)
            mutated[k] = m
        out = compute_fn(**mutated, i=i, **kwargs)
        assert out.keys() == baseline.keys(), "feature set changed under future mutation"
        for key in baseline:
            assert _equalish(baseline[key], out[key]), (
                f"feature '{key}' leaks future data: {baseline[key]} != {out[key]}"
            )
    return baseline
