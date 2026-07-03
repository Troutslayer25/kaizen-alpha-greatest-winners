"""Mechanical quarantine of future-derived move OUTCOMES from features (review PIT 3.8).

The move detector's outputs (magnitude, MFE, MAE, peak date, duration, lead time, significance
percentile) are known only AFTER the move resolves. They are valid as labels/descriptors but
must NEVER enter the feature set — a single join of gws.moves.total_pct_gain into a feature table
would leak the future. The [FORWARD] persistence layer's quarantine was convention + schema
comment; this makes it a standing, automated check runnable at every gate:

  assert_no_outcome_leak(feature_names)   — no feature name is (or embeds) a move-outcome column.
  module_touches_move_outcomes(module)    — a feature module does not import the detector/labeler.
"""
from __future__ import annotations

from gws.phase_a1.move_characterization import DESCRIPTOR_FIELDS

# Forward-derived outcome columns of gws.moves — never legal as features. Derived from
# DESCRIPTOR_FIELDS (review F1) so every current AND future move descriptor is auto-quarantined;
# the inception_context fields are PIT (data <= trough) and are deliberately NOT here.
MOVE_OUTCOME_COLUMNS = frozenset({
    "total_pct_gain", "magnitude", "mfe", "mae", "max_intra_drawdown",
    "peak_date", "duration_days", "magnitude_pctile", "pctile_basis",
    "lead_time_days", "linked_move_id", "trough_idx", "peak_idx", "is_open",
}) | set(DESCRIPTOR_FIELDS)
# Substrings that betray an outcome even inside a longer feature name.
_OUTCOME_TOKENS = ("total_pct_gain", "magnitude", "_mfe", "mfe_", "_mae", "mae_",
                   "peak_date", "lead_time", "linked_move", "pctile")


def assert_no_outcome_leak(feature_names) -> None:
    """Raise if any feature name equals or embeds a move-outcome quantity."""
    names = list(feature_names)
    exact = set(names) & MOVE_OUTCOME_COLUMNS
    embedded = {n for n in names if any(tok in n for tok in _OUTCOME_TOKENS)}
    bad = exact | embedded
    if bad:
        raise AssertionError(
            f"feature names leak move outcomes (future-derived): {sorted(bad)} — these are "
            f"labels/descriptors, never features (review PIT 3.8)")


def module_touches_move_outcomes(module) -> bool:
    """True if a feature module's source references the detector/labeler (it must not)."""
    import inspect
    src = inspect.getsource(module)
    return any(bad in src for bad in ("move_detector", "trough_detector", "phase_a1.labeling",
                                      "gws.moves", "move_characterization", "persist_moves",
                                      "query.moves", "MoveQuery"))
