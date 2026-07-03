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


def _mutate_future(v, i, n, rng):
    m = v.copy()
    if i + 1 < n:
        m[i + 1:] = m[i + 1:] * rng.uniform(0.5, 1.5, size=n - i - 1)
    return m


def assert_future_invariant(compute_fn, series: dict, i, *, n_trials=5, seed=0, **kwargs):
    """Assert compute_fn(...at i...) does not depend on any bar after `i`.

    `compute_fn` is called as compute_fn(**series_at_i, i, **kwargs) where each value
    in `series` is a 1-D array passed by its keyword name. We compute the baseline, then
    repeatedly perturb the future and recompute; all feature values must be unchanged.

    Three complementary mutations (review, code-quality) close the earlier blind spots:
      * VALUE — multiplicatively randomize every bar after i (catches value leaks);
      * LENGTH — truncate/extend the array past i by a random number of bars (catches leaks
        via len(series) / future-NaN structure / future zero counts, which value scaling
        preserves);
      * KWARGS — any ARRAY-valued kwarg (e.g. a benchmark passed by keyword) is mutated too,
        so a full-series array smuggled through kwargs is no longer invisible.

    HARD REQUIREMENT: any future-spanning array a feature reads MUST be passed in `series` or as
    an array kwarg — never captured in a closure — or this harness cannot see it.

    Returns the baseline feature dict on success; raises AssertionError on leakage.
    """
    rng = np.random.default_rng(seed)
    base_arrays = {k: np.asarray(v, float) for k, v in series.items()}
    base_kwargs = {k: (np.asarray(v, float) if _is_array(v) else v) for k, v in kwargs.items()}
    baseline = compute_fn(**base_arrays, i=i, **base_kwargs)

    n = len(next(iter(base_arrays.values())))
    for trial in range(n_trials):
        mut_arrays = {k: _mutate_future(v, i, n, rng) for k, v in base_arrays.items()}
        mut_kwargs = {k: (_mutate_future(v, i, len(v), rng) if _is_array(v) else v)
                      for k, v in base_kwargs.items()}
        # LENGTH mutation on odd trials: truncate the future tail so the array length changes
        # (catches leaks via len(series) / future-NaN structure that value scaling preserves).
        if trial % 2 == 1 and n > i + 1:
            j = int(rng.integers(i + 1, n))                # keep [0, j); j in [i+1, n) -> len < n
            mut_arrays = {k: v[:j] for k, v in mut_arrays.items()}
            mut_kwargs = {k: (v[:j] if _is_array(v) and len(v) == n else v)
                          for k, v in mut_kwargs.items()}
        out = compute_fn(**mut_arrays, i=i, **mut_kwargs)
        assert out.keys() == baseline.keys(), "feature set changed under future mutation"
        for key in baseline:
            assert _equalish(baseline[key], out[key]), (
                f"feature '{key}' leaks future data: {baseline[key]} != {out[key]}"
            )
    return baseline


def _is_array(v):
    return isinstance(v, np.ndarray) or (isinstance(v, (list, tuple)) and len(v) > 0
                                         and isinstance(v[0], (int, float)))
