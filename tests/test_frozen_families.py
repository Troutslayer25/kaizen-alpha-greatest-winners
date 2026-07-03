"""M-1: the frozen FDR family map is code-enforced (no ad-hoc regrouping)."""
import pytest

from gws.phase_a2.feature_catalog import FROZEN_FAMILIES, build_families, family_of


def test_family_of_maps_stems_and_generic():
    assert family_of("dist_from_high_63") == "location"
    assert family_of("vol_trend_21") == "volume"
    assert family_of("hurst_100") == "generic"
    assert family_of("not_a_feature_9") is None


def test_build_families_groups_and_rejects_unmapped():
    fams = build_families({"dist_from_high_21": 0.01, "dist_from_low_63": 0.2, "atr_pct_21": 0.4})
    assert set(fams) == {"location", "volatility"}
    assert len(fams["location"]) == 2
    with pytest.raises(ValueError, match="no frozen family"):
        build_families({"mystery_feature_21": 0.01})       # regrouping guard


def test_the_seven_precommitted_families_are_present():
    assert set(FROZEN_FAMILIES.values()) == {
        "volatility", "location", "moving_average", "volume",
        "base_structure", "relative_strength", "group_strength"}
