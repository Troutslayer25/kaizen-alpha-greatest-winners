import numpy as np

from gws.phase_a3.findings_hierarchy import classify_finding, Tolerances
from gws.phase_a3.backtest import decile_lift, capacity_diagnostic


def test_tier1_when_all_criteria_met():
    r = classify_finding(wf_consistency=0.80, worst_fold_auc=0.55,
                         effect_retention=0.60, significant_after_neutralization=True,
                         pretrough_actionable=True)
    assert r["tier"] == 1
    assert all(r["passed"].values())


def test_tier2_when_walk_forward_consistency_misses():
    r = classify_finding(wf_consistency=0.50, worst_fold_auc=0.55,
                         effect_retention=0.60, significant_after_neutralization=True,
                         pretrough_actionable=True)
    assert r["tier"] == 2
    assert r["passed"]["neutralization"] and not r["passed"]["walk_forward"]


def test_catastrophic_fold_blocks_tier1():
    r = classify_finding(wf_consistency=0.90, worst_fold_auc=0.40,   # one fold reverses badly
                         effect_retention=0.60, significant_after_neutralization=True,
                         pretrough_actionable=True)
    assert r["tier"] == 2                                            # neutralization holds, WF fails


def test_tier3_when_neutralization_fails():
    r = classify_finding(wf_consistency=0.90, worst_fold_auc=0.60,
                         effect_retention=0.20, significant_after_neutralization=False,
                         pretrough_actionable=True)
    assert r["tier"] == 3


def test_pretrough_requirement_can_block_tier1():
    r = classify_finding(wf_consistency=0.80, worst_fold_auc=0.55,
                         effect_retention=0.60, significant_after_neutralization=True,
                         pretrough_actionable=False)
    assert r["tier"] == 2                                            # hindsight-only -> not Tier 1


def test_decile_lift_monotone_for_real_signal():
    rng = np.random.default_rng(0)
    n = 2000
    score = rng.normal(0, 1, n)
    fwd = 0.05 * score + rng.normal(0, 0.05, n)                      # higher score -> higher return
    res = decile_lift(score, fwd)
    assert res["spread"] > 0
    assert res["monotonicity"] > 0.8
    assert res["top_mean"] > res["bottom_mean"]


def test_decile_lift_flat_for_noise():
    rng = np.random.default_rng(1)
    n = 2000
    res = decile_lift(rng.normal(0, 1, n), rng.normal(0, 0.05, n))
    assert abs(res["spread"]) < 0.02                                # no edge


def test_capacity_diagnostic_picks_top_names():
    scores = np.arange(100.0)
    adv = np.full(100, 10_000_000.0)
    res = capacity_diagnostic(scores, adv, top_frac=0.1, clip_pct=0.01)
    assert res["n_top"] == 10
    assert res["median_adv"] == 10_000_000.0
    assert np.isclose(res["aggregate_capacity"], 10 * 0.01 * 10_000_000.0)
