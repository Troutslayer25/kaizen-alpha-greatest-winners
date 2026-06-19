"""Method 4 — mutual information (Phase A3).

Non-parametric dependence between each feature and the target, capturing non-linear
relationships without distributional assumptions. Compared against univariate and
permutation-importance rankings — agreement across methods strengthens confidence.
"""
from __future__ import annotations

import numpy as np
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression


def feature_mutual_info(X, y, *, discrete_target: bool = True, seed: int = 0) -> np.ndarray:
    """MI between each column of X (n, d) and target y. discrete_target=True for the
    binary setup-vs-control target; False for a continuous target (e.g. magnitude)."""
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    y = np.asarray(y)
    fn = mutual_info_classif if discrete_target else mutual_info_regression
    return fn(X, y, random_state=seed)
