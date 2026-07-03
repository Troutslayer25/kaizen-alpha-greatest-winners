"""CF-3: magnitude percentiles must not leak the future move distribution into labels."""
import numpy as np
import pandas as pd
import pytest

from gws.phase_a1.significance import assign, expanding_pctile, frozen_train_pctile


def _moves(mags, dates):
    return pd.DataFrame({"total_pct_gain": mags,
                         "peak_date": pd.to_datetime(dates)})


def test_expanding_pctile_is_invariant_to_future_moves():
    # The single most important PIT property: an early move's percentile must be
    # byte-identical whether or not later moves exist in the frame.
    early = _moves([0.10, 0.50, 0.90], ["1975-01-01", "1975-06-01", "1975-12-01"])
    later = _moves([5.0, 6.0, 7.0], ["2020-01-01", "2020-06-01", "2020-12-01"])
    full = pd.concat([early, later], ignore_index=True)

    p_early_only = expanding_pctile(early)
    p_full = expanding_pctile(full).iloc[:len(early)].reset_index(drop=True)
    assert np.allclose(p_early_only.to_numpy(), p_full.to_numpy())


def test_expanding_pctile_first_move_is_top_of_its_own_world():
    m = _moves([0.3, 0.1, 0.9], ["2001-01-01", "2001-02-01", "2001-03-01"])
    p = expanding_pctile(m)
    assert p.iloc[0] == 1.0          # only move seen so far -> 100th pctile
    assert p.iloc[1] == pytest.approx(0.5)   # smaller than the one prior -> 1 of 2
    assert p.iloc[2] == pytest.approx(1.0)   # largest of the three so far


def test_frozen_train_ranks_all_against_train_block_only():
    df = _moves([1.0, 2.0, 3.0, 100.0], ["1990-01-01", "1990-02-01", "2021-01-01", "2021-02-01"])
    train_mask = df["peak_date"] <= pd.Timestamp("2000-01-01")   # first two moves only
    p = frozen_train_pctile(df, train_mask)
    # train ECDF is {1.0, 2.0}; a 2021 mega-move maps to 100th pctile of that frozen block,
    # and crucially the frozen edges do NOT shift because 2021 exists.
    assert p.iloc[0] == pytest.approx(0.5)
    assert p.iloc[1] == pytest.approx(1.0)
    assert p.iloc[3] == pytest.approx(1.0)


def test_full_sample_mode_is_rejected():
    df = _moves([1.0, 2.0], ["2000-01-01", "2001-01-01"])
    with pytest.raises(ValueError):
        assign(df, "full_sample")


def test_assign_stamps_basis_provenance():
    df = _moves([1.0, 2.0, 3.0], ["2000-01-01", "2000-06-01", "2001-01-01"])
    _, basis = assign(df, "expanding")
    assert (basis == "expanding").all()
    _, basis2 = assign(df, "frozen_train", train_end=pd.Timestamp("2000-12-31"))
    assert basis2.iloc[0].startswith("frozen_train:")
