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
}

# Generic/auto feature families (gws/phase_a2/generic_features.py). Listed here so a
# generic feature is auto-detected as 'auto_generated' even if a caller forgets the
# branch kwarg — it can never silently fall through to 'unclassified'.
GENERIC_PREFIXES = frozenset({
    "ret_autocorr1", "ret_skew", "ret_kurt", "zero_cross",
    "perm_entropy", "hurst", "vol_autocorr1",
})


def _prefix(feature_name: str) -> str:
    """Strip a trailing _<lookback> / _<period> from a feature name to get its family."""
    parts = feature_name.rsplit("_", 1)
    return parts[0] if len(parts) == 2 and parts[1].isdigit() else feature_name


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
