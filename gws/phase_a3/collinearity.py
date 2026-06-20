"""Collinearity / redundancy diagnostic (Phase A3, critique keeper).

A feature and a market-context regime score can be near-duplicates (e.g. an individual
price-to-200d-MA feature and a breadth regime built from the same 200d MAs aggregated).
Tree models (RF/XGB/LightGBM) are robust to this for PREDICTION — collinearity does not
inflate out-of-sample AUC — but it muddies feature-IMPORTANCE attribution (which of two
near-duplicates gets credit). This diagnostic surfaces such pairs so attribution stays
honest and the regime score can be checked for orthogonality against the price features.

It is a diagnostic, not an automatic transform: it does NOT silently residualize features
(that would bake in a transformation choice). The factor/industry neutralization step
(Method 2) already removes "this feature is just the trend in disguise"; this complements
it by reporting near-duplicate structure. Preference per design: build the regime score
from non-price factors (credit/macro) where possible, so it is orthogonal by construction.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def variance_inflation_factors(X: pd.DataFrame) -> pd.Series:
    """VIF per column: 1 / (1 - R^2) from regressing each column on all the others.
    VIF > 10 is the conventional severe-collinearity flag. NaN-rows dropped."""
    Z = X.dropna()
    cols = list(Z.columns)
    vifs = {}
    for c in cols:
        others = [o for o in cols if o != c]
        if not others:
            vifs[c] = 1.0
            continue
        A = np.column_stack([np.ones(len(Z)), Z[others].to_numpy()])
        y = Z[c].to_numpy()
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ beta
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - float((resid ** 2).sum()) / ss_tot if ss_tot > 0 else 0.0
        vifs[c] = float(1.0 / (1.0 - r2)) if r2 < 1 - 1e-12 else float("inf")
    return pd.Series(vifs)


def high_correlation_pairs(X: pd.DataFrame, threshold: float = 0.9) -> list[dict]:
    """Feature pairs with |Pearson corr| >= threshold — candidate near-duplicates.
    Returns [{a, b, corr}] sorted by descending |corr|."""
    corr = X.corr().to_numpy()
    cols = list(X.columns)
    out = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            c = corr[i, j]
            if c == c and abs(c) >= threshold:
                out.append({"a": cols[i], "b": cols[j], "corr": float(c)})
    return sorted(out, key=lambda d: -abs(d["corr"]))


def regime_collinearity(features: pd.DataFrame, regime_score, threshold: float = 0.9) -> list[dict]:
    """Flag individual features that are near-collinear with the market-context regime score
    (the circular-reasoning risk: the regime is an aggregate of the same price behavior).
    Returns [{feature, corr}] above threshold."""
    r = np.asarray(regime_score, float)
    out = []
    for c in features.columns:
        x = features[c].to_numpy(float)
        m = ~(np.isnan(x) | np.isnan(r))
        if m.sum() < 3 or np.std(x[m]) == 0 or np.std(r[m]) == 0:
            continue
        corr = float(np.corrcoef(x[m], r[m])[0, 1])
        if abs(corr) >= threshold:
            out.append({"feature": c, "corr": corr})
    return sorted(out, key=lambda d: -abs(d["corr"]))
