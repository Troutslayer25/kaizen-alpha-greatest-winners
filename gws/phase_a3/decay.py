"""Method 5 — feature decay (information coefficient by horizon) + pre-trough
actionability proof (Phase A3).

Discovers WHEN a feature predicts, not just whether, and proves the signal was
usable BEFORE the hindsight-identified trough. A feature whose predictive power
exists only at the exact trough and collapses at trough-5/-10/-20/-30 is a
hindsight artifact, disqualified from Tier 1. Results are written to
gws.feature_decay.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr, pearsonr

PRETROUGH_HORIZONS = (5, 10, 20, 30)


def information_coefficient(feature, target, method: str = "spearman") -> dict:
    """IC (rank or linear correlation) with its p-value and t-stat. NaN-safe."""
    f = np.asarray(feature, float)
    t = np.asarray(target, float)
    mask = ~(np.isnan(f) | np.isnan(t))
    f, t = f[mask], t[mask]
    n = len(f)
    if n < 3 or np.std(f) == 0 or np.std(t) == 0:
        return {"ic": float("nan"), "pvalue": float("nan"), "tstat": float("nan"), "n": n}
    rho, p = (spearmanr(f, t) if method == "spearman" else pearsonr(f, t))
    rho = float(rho)
    tstat = rho * np.sqrt((n - 2) / (1 - rho**2)) if abs(rho) < 1 else float("inf")
    return {"ic": rho, "pvalue": float(p), "tstat": float(tstat), "n": n}


def decay_curve(feature_by_horizon: dict, target, method: str = "spearman") -> list[dict]:
    """IC at each horizon (days before the trough). horizon 0 = at the trough."""
    return [
        {"horizon_days": h, **information_coefficient(feature_by_horizon[h], target, method)}
        for h in sorted(feature_by_horizon)
    ]


def pretrough_actionable(feature_by_horizon: dict, target, *,
                         required_horizons=PRETROUGH_HORIZONS, alpha: float = 0.05,
                         method: str = "spearman"):
    """True iff the feature has a statistically significant IC at the pre-trough
    horizons (not merely at the trough itself). Returns (ok, per-horizon detail)."""
    detail = {}
    ok = True
    for h in required_horizons:
        ic = information_coefficient(feature_by_horizon.get(h, []), target, method)
        detail[h] = ic
        if not (ic["pvalue"] == ic["pvalue"] and ic["pvalue"] < alpha):  # NaN-safe
            ok = False
    return ok, detail
