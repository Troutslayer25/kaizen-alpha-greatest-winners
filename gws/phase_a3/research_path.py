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
    BOTH levels to be promotable.

    Selection adjustment (review M-1). Members are tested only inside SELECTED families, which
    are enriched for small p-values; running member-level BH at the full `alpha` inflates the
    realized (selective) FDR. Per Benjamini & Bogomolov (2014), member BH runs at the reduced
    level `alpha * n_selected / n_families`, restoring control over the average FDR across the
    selected families."""
    names = list(families)
    n_families = len(names)
    fam_p = np.array([_simes_p(families[n]) for n in names])
    fam_rejected, _ = benjamini_hochberg(fam_p, alpha)
    n_selected = int(fam_rejected.sum())
    alpha_member = (alpha * n_selected / n_families) if n_families else alpha
    out = {}
    for name, surv in zip(names, fam_rejected):
        members = np.asarray(families[name], float)
        if surv and n_selected > 0:
            mem_rej, mem_q = benjamini_hochberg(members, alpha_member)
        else:
            mem_rej = np.zeros(len(members), bool)
            mem_q = np.full(len(members), np.nan)
        out[name] = {"family_significant": bool(surv),
                     "members_rejected": mem_rej, "member_qvalues": mem_q,
                     "alpha_member": alpha_member}
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


def estimate_sr_std(trial_srs) -> float:
    """Cross-trial dispersion of Sharpe estimates (review M-2) — the correct `sr_std` input to
    the deflation, estimated from the SET of strategy variants actually tried rather than the
    nonsensical 1.0 placeholder. Feed it every trial's per-observation Sharpe."""
    s = np.asarray([x for x in trial_srs if x == x], float)
    return float(np.std(s, ddof=1)) if s.size >= 2 else float("nan")


def lag1_autocorr(returns) -> float:
    """Lag-1 autocorrelation of a return series (for the effective-N deflation)."""
    r = np.asarray([x for x in returns if x == x], float)
    if r.size < 3 or np.std(r) == 0:
        return 0.0
    return float(np.corrcoef(r[:-1], r[1:])[0, 1])


def effective_n(n_obs: int, autocorr: float = 0.0) -> float:
    """Serial-correlation-deflated effective sample size n*(1-rho)/(1+rho) (review M-2). Strategy
    returns built from overlapping K-day forward windows are serially correlated; using raw
    n_obs overstates the effective sample and inflates the DSR."""
    ac = min(max(autocorr, -0.99), 0.99)
    return max(1.0, n_obs * (1.0 - ac) / (1.0 + ac))


def deflated_sharpe_ratio(observed_sr: float, n_obs: int, n_trials: int, *,
                          sr_std: float = 1.0, skew: float = 0.0, kurt: float = 3.0,
                          autocorr: float = 0.0) -> float:
    """Deflated Sharpe Ratio: probability the true Sharpe > the expected-max-under-N-trials
    benchmark, given non-normal returns. `observed_sr`/n_obs in per-observation units.
    Returns a probability in [0,1]; values near 1 survive the multiple-trials haircut.

    `sr_std` must be the cross-trial Sharpe dispersion (use estimate_sr_std), and `autocorr`
    the return series' lag-1 serial correlation so the effective sample size is deflated for
    overlap (review M-2) — the two inputs that were previously placeholders."""
    sr0 = expected_max_sharpe(n_trials, sr_std)
    denom = np.sqrt(max(1e-12, 1.0 - skew * observed_sr + ((kurt - 1.0) / 4.0) * observed_sr ** 2))
    n_eff = effective_n(n_obs, autocorr)
    z = (observed_sr - sr0) * np.sqrt(max(1.0, n_eff - 1.0)) / denom
    return float(norm.cdf(z))
