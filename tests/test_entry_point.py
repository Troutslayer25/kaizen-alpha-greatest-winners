"""Risk #2 instrument: the stop-conditioned metric fixes the stop-blind trap (P-1)."""
import types

import numpy as np

from gws.phase_a3.entry_point import (breakout_entries, entry_expectancy, forward_mfe_mae,
                                      population_overlap, stop_conditioned_outcome, trough_vs_breakout)


def test_stop_conditioned_catches_what_mfe_mae_misses():
    # The P-1 trap: entry, then -15% (blows a -8% stop), THEN rallies to +300%. Unstopped MFE/MAE
    # crowns it; the stop-conditioned metric correctly calls it a LOSS.
    path = [100.0] + list(np.linspace(100, 85, 8)) + list(np.linspace(85, 400, 60))
    close = np.array(path)
    mfe, mae = forward_mfe_mae(close, 0, horizon=80)
    assert mfe > 2.0 and mae < -0.10                     # looks spectacular, deep drawdown
    out = stop_conditioned_outcome(close, 0, target=0.20, stop=0.08, horizon=80)
    assert out["outcome"] == "loss"                      # stopped out before the MFE ever existed


def test_clean_breakout_entry_wins_under_stop():
    # A point of strength that runs to target without violating the stop -> a win.
    close = np.concatenate([np.full(1, 100.0), np.linspace(100, 130, 40)])
    out = stop_conditioned_outcome(close, 0, target=0.20, stop=0.08, horizon=40)
    assert out["outcome"] == "win"


def test_entry_expectancy_aggregates():
    close = np.linspace(100, 160, 200)                   # steady advance
    exp = entry_expectancy(close, [0, 50, 100], target=0.15, stop=0.08, horizon=80)
    assert exp["n"] == 3 and exp["win_rate"] == 1.0


def test_breakout_entries_are_points_of_strength_not_lows():
    close = np.concatenate([np.linspace(100, 90, 20), np.linspace(90, 150, 60)])
    move = types.SimpleNamespace(trough_idx=20, peak_idx=79)
    bo = breakout_entries(close, move, lookback=20)
    assert bo and all(b > 20 for b in bo)                # all after the trough (never the low)


def test_population_overlap():
    a = {(1, "d1"), (2, "d2"), (3, "d3")}
    b = {(2, "d2"), (3, "d3"), (4, "d4")}
    o = population_overlap(a, b)
    assert o["n_both"] == 2 and abs(o["jaccard"] - 0.5) < 1e-9
    assert o["only_a"] == [(1, "d1")] and o["only_b"] == [(4, "d4")]
