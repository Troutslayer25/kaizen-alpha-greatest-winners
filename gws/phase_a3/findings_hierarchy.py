"""Findings hierarchy — controlling research degrees of freedom (Phase A3).

Every finding is classified into a tier against PRE-COMMITTED tolerances, applied
mechanically (no subjective "but it's useful" override). Only Tier 1 is eligible
for the production model. Tolerances are starting values to be locked before results
are examined (OQ-19); they live here so the rule is auditable and version-controlled.

  Tier 1 — production candidate: predictive in >= wf_consistency_min of walk-forward
           folds with no catastrophic-reversal fold; retains >= retention_min of its
           raw effect after BOTH factor and industry neutralization while remaining
           significant; AND passes the pre-trough actionability requirement.
  Tier 2 — validated but not production-grade: survives neutralization & significant,
           but misses one Tier-1 criterion (e.g. walk-forward consistency).
  Tier 3 — exploratory: everything else.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tolerances:
    wf_consistency_min: float = 0.70      # min fraction of walk-forward folds predictive
    catastrophic_auc: float = 0.45        # any fold below this AUC disqualifies regardless
    retention_min: float = 0.50           # min fraction of raw effect surviving neutralization
    require_pretrough: bool = True        # pre-trough actionability mandatory for Tier 1


def classify_finding(*, wf_consistency: float, worst_fold_auc: float,
                     factor_retention: float, industry_retention: float,
                     significant_after_neutralization: bool,
                     pretrough_actionable: bool, tol: Tolerances = Tolerances()) -> dict:
    """Return {tier, passed:{...}} for a single finding. Maps onto findings_registry.

    Factor and industry neutralization are tracked SEPARATELY (Tier 1 requires the effect
    to survive BOTH while remaining significant), matching findings_registry's distinct
    passed_factor_neutralization / passed_industry_neutralization columns."""
    crit_wf = (wf_consistency >= tol.wf_consistency_min) and (worst_fold_auc >= tol.catastrophic_auc)
    passed_factor = factor_retention >= tol.retention_min
    passed_industry = industry_retention >= tol.retention_min
    crit_neut = passed_factor and passed_industry and significant_after_neutralization
    crit_action = pretrough_actionable if tol.require_pretrough else True

    if crit_wf and crit_neut and crit_action:
        tier = 1
    elif crit_neut:                       # statistically real & survives both neutralizations
        tier = 2
    else:
        tier = 3
    return {"tier": tier, "passed": {"walk_forward": crit_wf,
                                     "factor_neutralization": passed_factor,
                                     "industry_neutralization": passed_industry,
                                     "pretrough": crit_action}}
