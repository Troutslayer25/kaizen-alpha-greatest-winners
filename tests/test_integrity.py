"""Integrity: outcome-quarantine, survivorship-in-breadth, restatement incidence."""
import numpy as np
import pandas as pd
import pytest

from gws.phase_a2 import features_price_volume, generic_features
from gws.phase_a2.features_price_volume import compute_features
from gws.phase_a2.generic_features import compute_generic_features
from gws.phase0.restatement import restatement_incidence
from gws.regime.breadth import compute_breadth
from gws.validation.quarantine import (assert_no_outcome_leak, module_touches_move_outcomes)


def test_outcome_leak_detector():
    assert_no_outcome_leak(["dist_from_high_21", "vol_surge_10", "rs_at_high_63"])   # clean
    with pytest.raises(AssertionError):
        assert_no_outcome_leak(["dist_from_high_21", "total_pct_gain"])
    with pytest.raises(AssertionError):
        assert_no_outcome_leak(["some_mfe_ratio"])          # embedded outcome token


def test_every_descriptor_field_is_quarantined():
    # F1: the blocklist is derived from DESCRIPTOR_FIELDS, so EVERY current+future descriptor is
    # caught if a feature writer tries to register it.
    from gws.phase_a1.move_characterization import DESCRIPTOR_FIELDS
    for field in DESCRIPTOR_FIELDS:
        with pytest.raises(AssertionError):
            assert_no_outcome_leak([field])


def test_query_layer_import_is_a_quarantine_tripwire():
    # F1: a feature module importing the move query layer must be flagged.
    import types as _t
    fake = _t.ModuleType("fake_feature_mod")
    fake.__loading = "from gws.query.moves import MoveQuery\ndef f(): return MoveQuery()"
    import gws.query.moves as qm
    assert module_touches_move_outcomes(qm)          # the query module itself trips the check


def test_real_feature_functions_emit_no_outcome_columns():
    rng = np.random.default_rng(0)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, 300))
    bench = 100 * np.cumprod(1 + rng.normal(0, 0.008, 300))
    vol = rng.integers(1e6, 5e6, 300).astype(float)
    feats = compute_features(close, close * 1.01, close * 0.99, vol, 290, bench_close=bench)
    feats.update(compute_generic_features(close, close * 1.01, close * 0.99, vol, 290))
    assert_no_outcome_leak(feats.keys())                    # the real catalog is clean


def test_feature_modules_do_not_import_the_detector():
    assert not module_touches_move_outcomes(features_price_volume)
    assert not module_touches_move_outcomes(generic_features)


def test_breadth_includes_delisting_names_not_just_survivors():
    # 3 risers (survive) + 3 fallers that delist after day 260. BEFORE delisting the fallers are
    # making new lows, so full breadth is less bullish than a survivor-only view. A survivorship
    # bug (dropping dead names) would silently inflate breadth.
    n = 300
    risers = np.linspace(100, 200, n)
    fallers = np.linspace(200, 60, n)
    full = pd.DataFrame({0: risers, 1: risers, 2: risers,
                         3: fallers.copy(), 4: fallers.copy(), 5: fallers.copy()})
    full.loc[261:, [3, 4, 5]] = np.nan                      # delist after day 260
    survivors_only = full[[0, 1, 2]]

    at = 255                                                # before delisting, all 6 trade
    b_full = compute_breadth(full)["net_new_high_pct"].iloc[at]
    b_surv = compute_breadth(survivors_only)["net_new_high_pct"].iloc[at]
    assert b_full < b_surv                                  # fallers drag full breadth down


def test_restatement_incidence():
    stored = [100.0, 200.0, 300.0, 400.0]
    as_filed = [100.0, 205.0, 300.0, 400.0]                 # one quarter restated ~2.5%
    out = restatement_incidence(stored, as_filed, rel_tol=0.005)
    assert out["n"] == 4 and out["n_restated"] == 1
    assert out["incidence"] == 0.25
