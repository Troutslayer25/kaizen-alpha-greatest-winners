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
    VIF > 10 is the conventional severe-collinearity flag. NaN-rows dropped.

    Computed via the identity VIF_j = diag(inv(corr(X)))_jj (review, compute aspect): one
    correlation matrix + one inversion is O(n*d^2 + d^3), versus the O(n*d^3) column-by-column
    lstsq it replaces (~days -> minutes at n=11M, d=500). Numerically identical."""
    Z = X.dropna()
    cols = list(Z.columns)
    if len(cols) < 2:
        return pd.Series({c: 1.0 for c in cols})
    M = Z.to_numpy(float)
    sd = M.std(axis=0)
    good = sd > 0                                        # constant columns -> VIF undefined (inf)
    vifs = {c: float("inf") for c in cols}
    gcols = [c for c, g in zip(cols, good) if g]
    if len(gcols) < 2:
        return pd.Series({**{c: 1.0 for c in gcols}, **{c: vifs[c] for c in cols if c not in gcols}})
    R = np.corrcoef(M[:, good], rowvar=False)
    try:
        diag = np.diag(np.linalg.inv(R))
    except np.linalg.LinAlgError:
        diag = np.diag(np.linalg.pinv(R))               # perfect collinearity -> huge diag
    for c, d in zip(gcols, diag):
        vifs[c] = float("inf") if (not np.isfinite(d) or d > 1e10) else float(max(1.0, d))
    return pd.Series({c: vifs[c] for c in cols})


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
