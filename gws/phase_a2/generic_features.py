"""Generic / auto-generated feature bank (bias-control preventive complement).

Descriptors that no growth practitioner would naturally enumerate — permutation
entropy, return-distribution moments, autocorrelation structure, a rescaled-range
Hurst proxy, zero-crossing rate, volume autocorrelation. Their purpose is to let
practitioner-recognizable features compete on equal footing against a pool of
framework-neutral statistics, so the Gate A3->A4 motivation cross-tab is meaningful.
All tagged 'auto_generated' in the feature catalog.

Same interface and PIT guarantee as the Branch-1 features: a pure function of a single
ticker's series and an as-of index `i`, using only data on or before `i`.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import skew, kurtosis

DEFAULT_LOOKBACKS = (63, 126)


def permutation_entropy(series, order: int = 3) -> float:
    """Normalized ordinal-pattern (Bandt-Pompe) entropy in [0, 1]. A perfectly monotone
    series -> 0 (one pattern); a structureless series -> ~1."""
    x = np.asarray(series, float)
    n = len(x)
    if n < order + 1:
        return float("nan")
    counts: dict[tuple, int] = {}
    for i in range(n - order + 1):
        pat = tuple(np.argsort(x[i:i + order]))
        counts[pat] = counts.get(pat, 0) + 1
    p = np.array(list(counts.values()), float)
    p /= p.sum()
    ent = -(p * np.log(p)).sum()
    return float(ent / np.log(math.factorial(order)))


def hurst_rs(series) -> float:
    """Single-window rescaled-range Hurst proxy on log returns (~0.5 random, >0.5
    trending, <0.5 mean-reverting). A crude generic descriptor, not a precise estimate."""
    x = np.asarray(series, float)
    if len(x) < 20 or not (x > 0).all():
        return float("nan")
    r = np.diff(np.log(x))
    dev = np.cumsum(r - r.mean())
    rng = dev.max() - dev.min()
    s = r.std()
    if s == 0 or rng == 0:
        return float("nan")
    return float(np.log(rng / s) / np.log(len(r)))


def compute_generic_features(close, high, low, volume, i, *, lookbacks=DEFAULT_LOOKBACKS) -> dict:
    """Generic descriptors for the observation at index `i` (only data <= i used)."""
    close = np.asarray(close, float)
    volume = np.asarray(volume, float)
    feats: dict[str, float] = {}
    for lb in lookbacks:
        if i - lb + 1 < 0:
            continue
        w = close[i - lb + 1 : i + 1]
        if (w > 0).all():
            r = np.diff(np.log(w))
            if len(r) > 2 and r.std() > 0:
                feats[f"ret_autocorr1_{lb}"] = float(np.corrcoef(r[:-1], r[1:])[0, 1])
                feats[f"ret_skew_{lb}"] = float(skew(r))
                feats[f"ret_kurt_{lb}"] = float(kurtosis(r))
                feats[f"zero_cross_{lb}"] = float(np.mean(np.diff(np.sign(r)) != 0))
        feats[f"perm_entropy_{lb}"] = permutation_entropy(w, 3)
        feats[f"hurst_{lb}"] = hurst_rs(w)
        vw = volume[i - lb + 1 : i + 1]
        if len(vw) > 2 and vw.std() > 0:
            feats[f"vol_autocorr1_{lb}"] = float(np.corrcoef(vw[:-1], vw[1:])[0, 1])
    return feats
