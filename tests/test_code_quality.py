"""Code-quality hardening: meaningful embargo, harness length-leak catch, lead-0, gaps."""
import numpy as np
import pytest

from gws.common.pit_audit import assert_future_invariant
from gws.common.walkforward import expanding_splits
from gws.phase_a1.labeling import build_setup_labels
from gws.synthetic.generate import generate_panel


def test_embargo_removes_boundary_training_days():
    t = np.arange(1000)
    folds_no = list(expanding_splits(t, [600], label_horizon=5, embargo=0))
    folds_emb = list(expanding_splits(t, [600], label_horizon=5, embargo=20))
    tr0, _ = folds_no[0]
    tr1, _ = folds_emb[0]
    assert len(tr1) < len(tr0)                       # embargo drops boundary train obs
    assert t[tr1].max() < 600 - 20                   # nothing within 20 days before test start


def test_future_invariant_catches_a_length_leak():
    # A feature that reads len(series) is a future leak (the tail is unknown at i). The hardened
    # harness must catch it via the length mutation, which the value-only mutation missed.
    def leaky(close, i):
        return {"uses_len": float(len(close))}

    with pytest.raises(AssertionError):
        assert_future_invariant(leaky, {"close": np.ones(100)}, i=50, n_trials=6)


def test_future_invariant_passes_a_clean_feature():
    def clean(close, i):
        return {"px": float(close[i])}
    assert_future_invariant(clean, {"close": np.arange(100.0)}, i=50, n_trials=6)


def test_lead_zero_point_is_labeled_positive():
    import types
    moves = {0: [types.SimpleNamespace(trough_idx=300)]}
    df = build_setup_labels(moves, n_days=400, forward_window_k=20, min_index=252, sample_every=1)
    row = df[(df["ticker_id"] == 0) & (df["as_of_index"] == 300)].iloc[0]
    assert bool(row["label"]) and row["lead_time_days"] == 0    # standing on the trough = positive


def test_adversarial_panel_has_gaps():
    clean, _ = generate_panel(n_tickers=2, n_days=800, seed=1, adversarial=False)
    adv, _ = generate_panel(n_tickers=2, n_days=800, seed=1, adversarial=True)
    # adversarial daily returns reach larger extremes (flash crashes + overnight gaps)
    dr_clean = np.abs(np.diff(np.log(clean[clean["ticker_id"] == 0]["close"].to_numpy())))
    dr_adv = np.abs(np.diff(np.log(adv[adv["ticker_id"] == 0]["close"].to_numpy())))
    assert dr_adv.max() > dr_clean.max() * 2
