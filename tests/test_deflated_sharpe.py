"""M-2: deflated-Sharpe inputs are real, not placeholders."""
import numpy as np

from gws.phase_a3.research_path import (deflated_sharpe_ratio, effective_n, estimate_sr_std,
                                        lag1_autocorr)
from gws.phase_a3.trial_registry import TrialLog


def test_estimate_sr_std_recovers_dispersion():
    rng = np.random.default_rng(0)
    trials = rng.normal(0.05, 0.02, 500)
    assert abs(estimate_sr_std(trials) - 0.02) < 0.003


def test_effective_n_deflates_with_positive_autocorrelation():
    assert effective_n(1000, 0.0) == 1000
    assert effective_n(1000, 0.5) < 400          # (1-0.5)/(1+0.5) = 1/3
    assert effective_n(1000, 0.9) < 100


def test_overlap_lowers_confidence():
    # Same observed Sharpe; serially-correlated (overlapping) returns must yield a LOWER DSR
    # than the i.i.d. treatment, because the effective sample is smaller.
    iid = deflated_sharpe_ratio(0.06, n_obs=2000, n_trials=5, sr_std=0.02, autocorr=0.0)
    overlapped = deflated_sharpe_ratio(0.06, n_obs=2000, n_trials=5, sr_std=0.02, autocorr=0.8)
    assert overlapped < iid


def test_lag1_autocorr_detects_persistence():
    rng = np.random.default_rng(1)
    e = rng.normal(0, 1, 5000)
    ar = np.empty(5000)
    ar[0] = e[0]
    for t in range(1, 5000):
        ar[t] = 0.7 * ar[t - 1] + e[t]
    assert lag1_autocorr(ar) > 0.5


def test_trial_log_counts_and_collects_sharpes():
    log = TrialLog()
    log.record("h1", "A3", {"model": "xgb"}, sharpe=0.05)
    log.record("h1", "A3", {"model": "lgbm"}, sharpe=0.06)
    log.record("h1", "A3", {"model": "en"})           # no sharpe recorded
    assert log.n_trials == 3
    assert estimate_sr_std(log.sharpes()) == estimate_sr_std([0.05, 0.06])
