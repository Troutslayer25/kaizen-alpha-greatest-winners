"""Numeric-equality gate for vectorized features (compute aspect).

A vectorized feature may only replace its windowed per-point implementation once it is proven to
produce the SAME value at every sampled index (and NaN exactly where the per-point path omits the
feature). This harness is that gate — it is the reason the vectorization is safe to trust."""
from __future__ import annotations

import numpy as np


def assert_vectorized_matches_pointwise(vec: dict, point_fn, i_values, *, rtol=1e-9, atol=1e-12):
    """`vec` = {feature: full-length array} from the vectorized path; `point_fn(i) -> {feature:
    value}` the per-point path. For every sampled index and every vectorized feature:
      * if the per-point path EMITS the feature -> the two values must be close;
      * if it OMITS it (warm-up / degenerate) -> the vectorized value must be NaN.
    Raises AssertionError on the first mismatch."""
    for i in i_values:
        pt = point_fn(int(i))
        for feat, arr in vec.items():
            v = arr[i]
            if feat in pt:
                p = pt[feat]
                if p != p:                       # per-point NaN
                    assert v != v, f"{feat}@{i}: point=NaN vec={v}"
                else:
                    assert np.isclose(v, p, rtol=rtol, atol=atol), f"{feat}@{i}: vec={v} point={p}"
            else:
                assert v != v, f"{feat}@{i}: per-point omitted but vectorized={v} (expected NaN)"
    return True
