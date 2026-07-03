"""Harness A: the discovery funnel must be calibrated under the global null.

These tests encode the C-1 exhibit: naive i.i.d. inference is calibrated on independent rows
but catastrophically anti-conservative under ticker clustering. The clustered-inference fix
(task C-1) will add a test asserting the clustered screen pulls familywise back to ~alpha on
the SAME panels."""
import numpy as np

from gws.phase_a3.univariate import univariate_screen
from gws.validation.null_calibration import make_iid_panel, make_null_panel, run_calibration


def _naive(fm, labels, tickers):
    return univariate_screen(fm, labels, iid_ok=True)


def _clustered(fm, labels, tickers):
    return univariate_screen(fm, labels, cluster_ids=tickers)


def test_iid_naive_is_calibrated():
    # Independent rows: BH controls family-wise error at ~alpha. Proves the harness measures
    # real miscalibration rather than always failing.
    r = run_calibration(_naive, panel_fn=make_iid_panel, n_trials=80, alpha=0.05)
    assert r["familywise_rate"] <= 0.15


def test_clustered_naive_is_miscalibrated():
    # Ticker-clustered null: i.i.d. p-values are anti-conservative — the screen fires far above
    # alpha on features with zero true association. This is the C-1 defect the fix must repair.
    r = run_calibration(_naive, panel_fn=make_null_panel, n_trials=80, alpha=0.05)
    assert r["familywise_rate"] >= 0.5
    assert r["fp_rate"] > 0.10       # a large share of pure-null features rejected


def test_clustered_inference_restores_calibration():
    # The C-1 fix: cluster-robust inference on the SAME ticker-clustered null panels pulls the
    # family-wise rejection rate from ~1.0 (naive) back down to ~alpha.
    r = run_calibration(_clustered, panel_fn=make_null_panel, n_trials=80, alpha=0.05)
    assert r["familywise_rate"] <= 0.15
    assert r["fp_rate"] <= 0.05


def test_null_panel_has_the_intended_dependence():
    fm, labels, tickers = make_null_panel(seed=1)
    assert fm.shape[0] == len(labels) == len(tickers)
    assert set(np.unique(labels)) == {0, 1}
    # across-ticker variance in positive rate (the clustering that breaks naive inference)
    rates = [labels[tickers == g].mean() for g in np.unique(tickers)]
    assert np.std(rates) > 0.1
