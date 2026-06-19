"""Method 2 — cross-sectional factor and industry neutralization (Phase A3).

Many apparent signals are momentum/quality/size in disguise, or industry-cycle
effects, with no independent value. A feature that retains predictive power after
BOTH factor and industry neutralization is a genuinely independent signal — the
strongest class of finding. Neutralization is done by OLS residualization (factors)
and within-industry demeaning (industry); these feed the findings hierarchy.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr


def _ols_residual(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def factor_neutralize(feature, factors) -> np.ndarray:
    """Residual of `feature` after regressing on `factors` (1-D or 2-D, incl. intercept)."""
    feature = np.asarray(feature, float)
    factors = np.asarray(factors, float)
    if factors.ndim == 1:
        factors = factors[:, None]
    return _ols_residual(feature, factors)


def industry_neutralize(feature, industry) -> np.ndarray:
    """Within-industry demeaning (industry fixed effect removed)."""
    feature = np.asarray(feature, float)
    industry = np.asarray(industry)
    out = feature.copy()
    for g in np.unique(industry):
        m = industry == g
        out[m] = feature[m] - feature[m].mean()
    return out


def neutralize(feature, factors=None, industry=None) -> np.ndarray:
    f = np.asarray(feature, float)
    if factors is not None:
        f = factor_neutralize(f, factors)
    if industry is not None:
        f = industry_neutralize(f, industry)
    return f


def effect_retention(raw, residual, target, method: str = "spearman") -> float:
    """Fraction of a feature's raw predictive correlation that survives neutralization:
    |corr(residual, target)| / |corr(raw, target)|. Feeds the Tier-1 tolerance check."""
    raw = np.asarray(raw, float)
    residual = np.asarray(residual, float)
    target = np.asarray(target, float)
    corr = (lambda a, b: spearmanr(a, b).statistic) if method == "spearman" \
        else (lambda a, b: np.corrcoef(a, b)[0, 1])
    raw_c = abs(corr(raw, target))
    if raw_c == 0 or np.isnan(raw_c):
        return float("nan")
    return float(abs(corr(residual, target)) / raw_c)
