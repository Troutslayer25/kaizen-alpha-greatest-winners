import numpy as np

from gws.phase_a3.research_path import (
    hierarchical_fdr, expected_max_sharpe, deflated_sharpe_ratio,
)


def test_hierarchical_fdr_blocks_members_of_dead_families():
    families = {
        "real_family": [0.0001, 0.001, 0.6],        # strong family
        "null_family": [0.4, 0.7, 0.9],             # nothing here
    }
    out = hierarchical_fdr(families, alpha=0.05)
    assert out["real_family"]["family_significant"]
    assert out["real_family"]["members_rejected"].any()
    assert not out["null_family"]["family_significant"]
    # members of a non-significant family are never rejected, even a small p inside it
    assert not out["null_family"]["members_rejected"].any()


def test_hierarchical_fdr_protects_a_lone_small_p_in_a_dead_family():
    # One cherry-picked small p diluted by many noise members: Simes family p ~ p_min * n
    # won't clear, so the lone hit is not promoted (the forking-paths guard).
    rng = np.random.default_rng(0)
    families = {"noise": [0.02] + list(rng.uniform(0.4, 0.99, 19))}   # n=20
    out = hierarchical_fdr(families, alpha=0.05)
    assert not out["noise"]["family_significant"]
    assert not out["noise"]["members_rejected"].any()


def test_member_alpha_is_selection_adjusted():
    # M-1: with 1 of 4 families selected, members are tested at alpha * 1/4, not full alpha.
    fams = {"real": [1e-6, 1e-6, 1e-6], "n1": [.5, .6, .7],
            "n2": [.4, .8, .9], "n3": [.5, .5, .5]}
    out = hierarchical_fdr(fams, alpha=0.05)
    assert out["real"]["family_significant"]
    assert out["real"]["alpha_member"] == 0.05 * 1 / 4


def test_hierarchical_fdr_controls_member_fdr_under_null():
    # M-1 correctness: under the global null every rejection is false, so the member-level
    # family-wise rejection rate must sit at ~alpha, not above it.
    rng = np.random.default_rng(0)
    reps, false_reps = 400, 0
    for _ in range(reps):
        fams = {f"fam{i}": list(rng.uniform(0, 1, 10)) for i in range(8)}
        out = hierarchical_fdr(fams, alpha=0.05)
        false_reps += any(o["members_rejected"].any() for o in out.values())
    assert false_reps / reps <= 0.08


def test_expected_max_sharpe_grows_with_trials():
    assert expected_max_sharpe(2) < expected_max_sharpe(100) < expected_max_sharpe(10000)
    assert expected_max_sharpe(1) == 0.0


def test_deflated_sharpe_penalizes_many_trials():
    # Per-observation Sharpe units; sr_std = cross-trial Sharpe dispersion (must be supplied
    # consistently). Same observed Sharpe, more trials tried -> lower confidence it's real.
    dsr_few = deflated_sharpe_ratio(0.08, n_obs=2000, n_trials=5, sr_std=0.02)
    dsr_many = deflated_sharpe_ratio(0.08, n_obs=2000, n_trials=5000, sr_std=0.02)
    assert dsr_few > dsr_many
    # a strong per-obs Sharpe with few trials should be highly significant
    assert deflated_sharpe_ratio(0.08, n_obs=2000, n_trials=3, sr_std=0.02) > 0.9
