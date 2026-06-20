"""Research-path multiple-testing correction (Phase A3, critique keeper).

Feature-level BH-FDR (gws/common/stats.py) is necessary but undercounts the true search
space: features x lookbacks x detector scales x target definitions x control designs x
regimes x model classes x neutralization variants. This module adds:

  - hierarchical_fdr: family-level FDR first (a feature FAMILY, e.g. all MA-structure
    variants, must clear correction as a family before its members are inspected), then
    member-level FDR within surviving families. Controls the "garden of forking paths".
  - deflated_sharpe_ratio: the Bailey/Lopez de Prado haircut for strategy outputs — given
    that N strategy variants were tried, what is the probability the best one's Sharpe is
    truly > 0 rather than the expected maximum of N noise draws.

These complement, not replace, the marginal-sensitivity discipline (vary one design axis at
a time, not a full grid) that keeps the effective N from exploding in the first place.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

from gws.common.stats import benjamini_hochberg

_EULER = 0.5772156649015329


def _simes_p(pvals) -> float:
    """Simes combined p-value for a family (valid under positive dependence)."""
    p = np.sort(np.asarray([x for x in pvals if x == x], float))   # drop NaN
    n = len(p)
    if n == 0:
        return float("nan")
    return float(np.min(p * n / np.arange(1, n + 1)))


def hierarchical_fdr(families: dict, alpha: float = 0.05) -> dict:
    """`families`: {family_name: [member p-values]}. Returns
    {family_name: {family_significant, members_rejected: bool[]}} where member testing only
    occurs inside families that themselves survive family-level BH-FDR. A finding must clear
    BOTH levels to be promotable."""
    names = list(families)
    fam_p = np.array([_simes_p(families[n]) for n in names])
    fam_rejected, _ = benjamini_hochberg(fam_p, alpha)
    out = {}
    for name, surv in zip(names, fam_rejected):
        members = np.asarray(families[name], float)
        if surv:
            mem_rej, mem_q = benjamini_hochberg(members, alpha)
        else:
            mem_rej = np.zeros(len(members), bool)
            mem_q = np.full(len(members), np.nan)
        out[name] = {"family_significant": bool(surv),
                     "members_rejected": mem_rej, "member_qvalues": mem_q}
    return out


def expected_max_sharpe(n_trials: int, sr_std: float = 1.0) -> float:
    """Expected maximum Sharpe achievable by chance across `n_trials` independent strategy
    variants (Bailey & Lopez de Prado). `sr_std` = cross-trial dispersion of Sharpe estimates
    (estimate it from the trial set; 1.0 is a placeholder)."""
    if n_trials < 2:
        return 0.0
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(sr_std * ((1.0 - _EULER) * z1 + _EULER * z2))


def deflated_sharpe_ratio(observed_sr: float, n_obs: int, n_trials: int, *,
                          sr_std: float = 1.0, skew: float = 0.0, kurt: float = 3.0) -> float:
    """Deflated Sharpe Ratio: probability the true Sharpe > the expected-max-under-N-trials
    benchmark, given non-normal returns. `observed_sr`/n_obs in per-observation units.
    Returns a probability in [0,1]; values near 1 survive the multiple-trials haircut."""
    sr0 = expected_max_sharpe(n_trials, sr_std)
    denom = np.sqrt(max(1e-12, 1.0 - skew * observed_sr + ((kurt - 1.0) / 4.0) * observed_sr ** 2))
    z = (observed_sr - sr0) * np.sqrt(max(1, n_obs - 1)) / denom
    return float(norm.cdf(z))
