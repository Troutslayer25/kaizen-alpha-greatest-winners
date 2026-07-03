"""Method 2 — cross-sectional factor and industry neutralization (Phase A3).

Many apparent signals are momentum/quality/size in disguise, or industry-cycle
effects, with no independent value. A feature that retains predictive power after
BOTH factor and industry neutralization is a genuinely independent signal — the
strongest class of finding. Neutralization is done by OLS residualization (factors)
and within-industry demeaning (industry); these feed the findings hierarchy.

NEUTRALIZATION IS CROSS-SECTIONAL, PER DATE (review M-4). Factor loadings and industry means
are strongly time-varying; a single OLS/demean pooled across the whole 1950-2025 panel
residualizes against a 75-year-average exposure that describes no actual era, so a
momentum/industry-in-disguise feature can pass neutralization purely because the pooled beta
underfits a given era. Pass `dates` (one label per observation) to residualize within each
date's cross-section. The pooled path (dates=None) is retained only for single-cross-section
callers and tests. For a study whose premise is regime-dependence, a regime-pooled neutralizer
is internally inconsistent — production code must pass dates.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr


def _ols_residual(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def _by_date(fn, feature, dates, *args):
    """Apply a residualizer within each date's cross-section."""
    feature = np.asarray(feature, float)
    dates = np.asarray(dates)
    out = np.empty_like(feature)
    for d in np.unique(dates):
        m = dates == d
        sub = [a[m] if a is not None else None for a in args]
        out[m] = fn(feature[m], *sub)
    return out


def factor_neutralize(feature, factors, *, dates=None) -> np.ndarray:
    """Residual of `feature` after regressing on `factors` (1-D or 2-D, incl. intercept).
    With `dates`, the regression is run within each date (per-date cross-section)."""
    feature = np.asarray(feature, float)
    factors = np.asarray(factors, float)
    if factors.ndim == 1:
        factors = factors[:, None]
    if dates is None:
        return _ols_residual(feature, factors)

    def _one(f, X):
        # fall back to demeaning where a date has too few rows to fit the factors
        return _ols_residual(f, X) if len(f) > X.shape[1] + 1 else f - f.mean()
    return _by_date(_one, feature, dates, factors)


def industry_neutralize(feature, industry, *, dates=None) -> np.ndarray:
    """Within-industry demeaning (industry fixed effect removed). With `dates`, demeaning is
    within each (date, industry) cell so the industry effect removed is the CONTEMPORANEOUS
    one, not a 75-year average."""
    feature = np.asarray(feature, float)
    industry = np.asarray(industry)

    def _one(f, ind):
        out = f.copy()
        for g in np.unique(ind):
            mg = ind == g
            out[mg] = f[mg] - f[mg].mean()
        return out
    if dates is None:
        return _one(feature, industry)
    return _by_date(_one, feature, dates, industry)


def neutralize(feature, factors=None, industry=None, *, dates=None) -> np.ndarray:
    f = np.asarray(feature, float)
    if factors is not None:
        f = factor_neutralize(f, factors, dates=dates)
    if industry is not None:
        f = industry_neutralize(f, industry, dates=dates)
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
