import numpy as np

from gws.phase_a2.feature_catalog import motivation_for, catalog_rows, MOTIVATIONS
from gws.phase_a2.generic_features import (
    permutation_entropy, hurst_rs, compute_generic_features,
)
from gws.common.pit_audit import assert_future_invariant


# ---- motivation tagging ----

def test_motivation_tags():
    assert motivation_for("atr_pct_21") == "generic_statistical"
    assert motivation_for("rel_strength_63") == "practitioner_derived"
    assert motivation_for("dist_from_high_126") == "practitioner_derived"
    assert motivation_for("perm_entropy_63", branch="generic") == "auto_generated"


def test_catalog_rows_carry_valid_motivations():
    rows = catalog_rows(["atr_pct_21", "rel_strength_63", "ma_compression"])
    assert all(r["motivation"] in MOTIVATIONS for r in rows)
    assert {r["feature_name"] for r in rows} == {"atr_pct_21", "rel_strength_63", "ma_compression"}


# ---- generic feature bank ----

def test_permutation_entropy_monotone_vs_random():
    monotone = np.arange(200, dtype=float)
    rnd = np.random.default_rng(0).normal(0, 1, 200)
    assert permutation_entropy(monotone) < 0.05          # one ordinal pattern -> ~0
    assert permutation_entropy(rnd) > 0.8                # structureless -> near max


def test_hurst_finite_on_trending_series():
    x = 100 * np.cumprod(1 + np.random.default_rng(1).normal(0.0005, 0.01, 300))
    h = hurst_rs(x)
    assert np.isfinite(h) and 0.0 < h < 1.5


def test_generic_features_present_and_finite():
    rng = np.random.default_rng(2)
    close = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, 400))
    vol = rng.integers(1e6, 5e6, 400).astype(float)
    hi, lo = close * 1.001, close * 0.999
    f = compute_generic_features(close, hi, lo, vol, 380)
    assert "perm_entropy_63" in f and "hurst_126" in f and "ret_skew_63" in f
    assert all(np.isfinite(v) for v in f.values())


def test_generic_features_are_future_invariant():
    rng = np.random.default_rng(3)
    close = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, 400))
    vol = rng.integers(1e6, 5e6, 400).astype(float)
    hi, lo = close * 1.001, close * 0.999
    assert_future_invariant(
        compute_generic_features,
        {"close": close, "high": hi, "low": lo, "volume": vol},
        i=380,
    )
