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


def test_whole_entity_exclusion_makes_all_dates_ineligible():
    # C2: a stale-adjustment / unfetchable entity must be ineligible everywhere, even though its
    # bars look clean and it's a member.
    n = 300
    d = _dates(n)
    rows = build_eligibility(d, np.full(n, 50.0), np.full(n, 1e6), [(d[0], None)], entity_excluded=True)
    assert not any(r["eligible"] for r in rows)
    assert all(r["index_member"] and r["data_valid"] for r in rows)


def test_non_member_is_ineligible_even_if_clean():
    n = 300
    d = _dates(n)
    rows = build_eligibility(d, np.full(n, 50.0), np.full(n, 1e6), [])   # never a member
    assert not any(r["eligible"] for r in rows)
    assert rows[299]["data_valid"] and rows[299]["above_min_price"]      # clean, just not a member


def test_deep_era_all_listed_rule():
    # Ratified 2026-07-24: before INDEX_GATE_START (1990-07-03) the index gate is not applied —
    # a clean, seasoned, never-a-member name IS eligible (all-listed-equity); on/after the
    # boundary the same name is not. Membership stays recorded where intervals cover a date.
    n = 600
    base = dt.date(1989, 1, 2)
    d = [base + dt.timedelta(days=i) for i in range(n)]        # spans the 1990-07-03 boundary
    rows = build_eligibility(d, np.full(n, 50.0), np.full(n, 1e6), [])   # no membership data
    boundary = dt.date(1990, 7, 3)
    pre = [r for r in rows[251:] if r["date"] < boundary]
    post = [r for r in rows[251:] if r["date"] >= boundary]
    assert pre and post                                        # test actually spans the boundary
    assert all(r["eligible"] for r in pre)
    assert not any(r["eligible"] for r in post)
    assert not any(r["index_member"] for r in rows)            # nothing invented
