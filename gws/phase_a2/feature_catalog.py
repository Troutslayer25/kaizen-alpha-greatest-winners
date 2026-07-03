"""Feature provenance / motivation registry (bias control).

Extends the prior-code provenance idea (auditor framework §1A) from CODE to FEATURES.
Every feature is tagged with its ORIGIN — why it entered the catalog — *before* results
are seen. This is an honesty instrument (Auditor 4), not an objective property: tag by
the analyst's motivation, not by whether a practitioner happens to have a name for the
math. At Gate A3->A4 the surviving (Tier-1) findings are cross-tabbed by motivation to
answer: did the signals come from generic discovery, or are they dressed-up
practitioner concepts? (The latter is not disqualifying — but it must be visible.)

Tagging is diagnostic, not preventive. The preventive complement is the generic/auto
feature bank (gws/phase_a2/generic_features.py): practitioner-recognizable features must
compete against a large pool of descriptors no practitioner would enumerate, so the
cross-tab is meaningful rather than trivially "all practitioner-derived".
"""
from __future__ import annotations

MOTIVATIONS = (
    "theory_motivated",      # derived from an explicit economic/structural hypothesis
    "practitioner_derived",  # recognizable growth-investing concept (RS, base, proximity-to-high)
    "generic_statistical",   # plain descriptive statistic with no practitioner framing
    "auto_generated",        # programmatic/combinatorial or generic time-series descriptor
)

# Branch-1 price/volume feature families -> motivation, by prefix. Conservative tagging:
# anything carrying a recognizable practitioner concept is 'practitioner_derived' even if
# the math is generic, so the cross-tab does not understate practitioner influence.
PRICE_VOLUME_MOTIVATION = {
    "atr_pct": "generic_statistical",
    "ret_std": "generic_statistical",
    "dist_from_low": "generic_statistical",
    "vol_ratio": "generic_statistical",
    "vol_surge": "generic_statistical",
    "vol_trend": "generic_statistical",
    "range_tightness": "practitioner_derived",
    "dist_from_high": "practitioner_derived",
    "price_to_ma": "practitioner_derived",
    "ma_compression": "practitioner_derived",
    "updown_vol": "practitioner_derived",
    "accum_vol_share": "practitioner_derived",       # accumulation concept
    "up_vs_down_vol_extreme": "practitioner_derived", # accumulation dominance: biggest buying vs biggest selling day
    "cmf": "practitioner_derived",                    # Chaikin money flow (named indicator)
    "rel_strength": "practitioner_derived",
    # consolidation / base-structure family
    "base_depth": "practitioner_derived",
    "range_position": "practitioner_derived",
    "vol_contraction": "practitioner_derived",
    "tight_days_share": "practitioner_derived",
    # relative-strength line family
    "rs_line_slope": "practitioner_derived",
    "rs_at_high": "practitioner_derived",
    # group / sector strength (gws/phase_a2/group_strength.py)
    "sector_rs": "practitioner_derived",
    "sector_rs_slope": "practitioner_derived",
    "group_strength": "practitioner_derived",
}

# Generic/auto feature families (gws/phase_a2/generic_features.py). Listed here so a
# generic feature is auto-detected as 'auto_generated' even if a caller forgets the
# branch kwarg — it can never silently fall through to 'unclassified'.
GENERIC_PREFIXES = frozenset({
    "ret_autocorr1", "ret_skew", "ret_kurt", "zero_cross",
    "perm_entropy", "hurst", "vol_autocorr1",
})


# The family taxonomy is FDR-LOAD-BEARING (review M-1): hierarchical_fdr corrects at the
# family level, so how features group into families changes what clears correction. The
# prefix strip below is only the DEFAULT grouping; the authoritative, frozen family map is
# pre-committed in phases/PHASE_A2_PRECOMMIT.md before any A3 result is seen. Re-grouping a
# strong member out of a noisy family post-hoc is an FDR-gaming vector — it must go through a
# committed change to that map, not a silent rename.
def _prefix(feature_name: str) -> str:
    """Strip a trailing _<lookback> / _<period> from a feature name to get its family."""
    parts = feature_name.rsplit("_", 1)
    return parts[0] if len(parts) == 2 and parts[1].isdigit() else feature_name


# FROZEN FDR family map (review M-1) — the authoritative, code-enforced version of the prose in
# phases/PHASE_A2_PRECOMMIT.md. feature stem -> family. This is the ONLY sanctioned grouping for
# hierarchical_fdr; a silent regroup (worth ~10x in promotion odds) now diffs in git.
FROZEN_FAMILIES = {
    "atr_pct": "volatility", "ret_std": "volatility",
    "dist_from_high": "location", "dist_from_low": "location", "range_position": "location",
    "price_to_ma": "moving_average", "ma_compression": "moving_average",
    "vol_ratio": "volume", "vol_surge": "volume", "vol_trend": "volume", "updown_vol": "volume",
    "accum_vol_share": "volume", "up_vs_down_vol_extreme": "volume", "cmf": "volume",
    "base_depth": "base_structure", "vol_contraction": "base_structure",
    "tight_days_share": "base_structure", "range_tightness": "base_structure",
    "rel_strength": "relative_strength", "rs_line_slope": "relative_strength", "rs_at_high": "relative_strength",
    "sector_rs": "group_strength", "sector_rs_slope": "group_strength", "group_strength": "group_strength",
}
GENERIC_FAMILY = "generic"


def family_of(feature_name: str) -> str | None:
    """Frozen family for a feature (None if unmapped). Generic-bank features are one `generic` family."""
    pre = _prefix(feature_name)
    if pre in GENERIC_PREFIXES:
        return GENERIC_FAMILY
    return FROZEN_FAMILIES.get(pre)


def build_families(feature_pvalues: dict) -> dict:
    """Group {feature_name: pvalue} into the frozen family map for hierarchical_fdr — the ONLY
    sanctioned constructor (review M-1). RAISES on an unmapped feature so a member cannot be
    regrouped into a friendlier family in an analysis script without a committed change here."""
    fams: dict = {}
    for feat, p in feature_pvalues.items():
        fam = family_of(feat)
        if fam is None:
            raise ValueError(f"feature '{feat}' has no frozen family — add it to FROZEN_FAMILIES "
                             f"(and PHASE_A2_PRECOMMIT.md) before FDR; no ad-hoc regrouping")
        fams.setdefault(fam, []).append(p)
    return fams


def motivation_for(feature_name: str, *, branch: str = "price_volume") -> str:
    """Return the motivation tag for a feature. Generic-bank features are
    'auto_generated' (by branch or by auto-detected prefix); Branch-1 families map via
    the table above."""
    pre = _prefix(feature_name)
    if branch == "generic" or pre in GENERIC_PREFIXES:
        return "auto_generated"
    return PRICE_VOLUME_MOTIVATION.get(pre, "unclassified")


def catalog_rows(feature_names, *, branch: str = "price_volume", formula_version: str = "v1"):
    """Build gws.feature_catalog rows (dicts) for a set of feature names, with motivation
    tagged. Intended to be committed before any A3 result is examined.

    Fail-closed: every emitted motivation must be a known tag. An 'unclassified' result
    means a feature family was added without a motivation entry — that is a wiring error
    and must be fixed at registration, not silently shipped."""
    rows = []
    for fn in feature_names:
        m = motivation_for(fn, branch=branch)
        if m not in MOTIVATIONS:
            raise ValueError(
                f"feature '{fn}' has motivation '{m}' — add it to PRICE_VOLUME_MOTIVATION "
                f"or GENERIC_PREFIXES before cataloging (no unclassified features ship)")
        rows.append({"feature_name": fn, "branch": branch,
                     "formula_version": formula_version, "motivation": m, "status": "active"})
    return rows
