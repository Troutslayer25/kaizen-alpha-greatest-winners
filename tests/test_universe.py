"""Phase 0: PIT universe eligibility (pure core)."""
import datetime as dt

import numpy as np

from gws.phase0.universe import build_eligibility, member_flags


def _dates(n):
    base = dt.date(2000, 1, 3)
    return [base + dt.timedelta(days=i) for i in range(n)]


def test_member_flags_from_intervals():
    d = _dates(10)
    flags = member_flags(d, [(d[2], d[4]), (d[7], None)])   # member 2..4 and 7..end
    assert list(flags) == [False, False, True, True, True, False, False, True, True, True]


def test_eligibility_requires_all_gates():
    n = 300
    d = _dates(n)
    close = np.full(n, 50.0)
    volume = np.full(n, 1e6)
    rows = build_eligibility(d, close, volume, [(d[0], None)])   # member the whole time
    # before 252 bars: ineligible on history alone even though member/valid/priced
    assert rows[250]["index_member"] and rows[250]["data_valid"] and not rows[250]["eligible"]
    assert rows[251]["eligible"]                               # 252nd bar -> eligible


def test_penny_and_untraded_bars_fail_data_validity():
    n = 300
    d = _dates(n)
    close = np.full(n, 50.0); close[260] = 0.4                # sub-$1 -> above_min_price False
    volume = np.full(n, 1e6); volume[261] = 0                 # untraded -> data_valid False
    rows = build_eligibility(d, close, volume, [(d[0], None)])
    assert not rows[260]["above_min_price"] and not rows[260]["eligible"]
    assert not rows[261]["data_valid"] and not rows[261]["eligible"]


def test_non_member_is_ineligible_even_if_clean():
    n = 300
    d = _dates(n)
    rows = build_eligibility(d, np.full(n, 50.0), np.full(n, 1e6), [])   # never a member
    assert not any(r["eligible"] for r in rows)
    assert rows[299]["data_valid"] and rows[299]["above_min_price"]      # clean, just not a member
