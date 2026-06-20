"""Empirical liquidity-floor / knee-of-curve utility.

v2 (2026-06-20): this is NOT a universe-eligibility gate. The institutional ADV floor was
removed from universe construction (see phases/PHASE0_PRECOMMIT.md Rev v2) — liquidity is
carried as a feature for A3 to discover, and capacity is applied at the deployment layer.
This module is retained ONLY as a non-gating liquidity-tier / capacity bucketing utility.

The knee is discovered, not fixed: for each period it is the natural break
in the annual 50-day ADV distribution below which stocks become genuinely illiquid.
The break is found by the knee-of-curve of the sorted log10(ADV) distribution (the
point of maximum perpendicular distance from the chord joining its endpoints). Run
separately per period (1950-2009 vs 2010-present), since market dollar-volume levels
differ across eras. Pre-committed before any floor values are examined.
"""
from __future__ import annotations

import numpy as np


def knee_index(curve) -> int:
    """Index of the knee: max perpendicular distance from the chord between endpoints
    of the (monotone) curve. Pure-numpy Kneedle-style detection (no dependency)."""
    y = np.asarray(curve, float)
    n = len(y)
    if n < 3:
        return 0
    xs = np.linspace(0, 1, n)
    ys = (y - y.min()) / (y.max() - y.min() + 1e-12)
    p1 = np.array([xs[0], ys[0]])
    p2 = np.array([xs[-1], ys[-1]])
    d = p2 - p1
    dn = d / np.linalg.norm(d)
    pts = np.column_stack([xs, ys]) - p1
    proj = pts @ dn
    perp = pts - np.outer(proj, dn)
    return int(np.argmax(np.linalg.norm(perp, axis=1)))


def discover_floor(adv_values) -> float:
    """Return the discovered ADV floor (in dollars) for one period's index-constituent
    universe. Stocks at or below the floor are treated as illiquid for that period."""
    v = np.asarray(adv_values, float)
    v = v[np.isfinite(v) & (v > 0)]
    if len(v) < 3:
        return float("nan")
    s = np.sort(np.log10(v))
    return float(10 ** s[knee_index(s)])
