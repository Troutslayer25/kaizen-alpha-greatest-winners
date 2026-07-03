"""C-1: the true lockbox is mechanically enforced."""
import datetime as dt

import numpy as np
import pytest

from gws.phase0.lockbox import LOCKBOX_START, assert_not_in_lockbox, drop_lockbox, in_lockbox
from gws.phase0.universe import build_eligibility


def test_in_lockbox_boundary():
    assert not in_lockbox(dt.date(2021, 12, 31))
    assert in_lockbox(LOCKBOX_START)
    assert in_lockbox(dt.date(2024, 6, 1))


def test_assert_and_drop():
    dates = [dt.date(2021, 6, 1), dt.date(2023, 1, 1)]
    with pytest.raises(PermissionError):
        assert_not_in_lockbox(dates)
    assert_not_in_lockbox(dates, unlock=True)             # explicit open is allowed
    kept, arr = drop_lockbox(dates, np.array([10.0, 20.0]))
    assert kept == [dt.date(2021, 6, 1)] and list(arr) == [10.0]


def test_eligibility_seals_the_holdout():
    # dates straddling the boundary; even a clean member is ineligible inside the lockbox.
    dates = [dt.date(2021, 1, 1) + dt.timedelta(days=i) for i in range(0, 900, 3)]
    n = len(dates)
    rows = build_eligibility(dates, np.full(n, 50.0), np.full(n, 1e6), [(dates[0], None)])
    for r in rows:
        if in_lockbox(r["date"]):
            assert not r["eligible"]
    # unlock=True restores eligibility inside the window (the terminal act)
    unlocked = build_eligibility(dates, np.full(n, 50.0), np.full(n, 1e6), [(dates[0], None)], unlock=True)
    assert any(in_lockbox(r["date"]) and r["eligible"] for r in unlocked)
