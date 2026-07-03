"""Lineage: return-space FMP<->Norgate comparison + contiguous-span collapsing."""
import numpy as np

from gws.phase0.completeness_audit import compare_return_series, daily_log_returns
from gws.phase0.spans import contiguous_spans


def test_contiguous_spans_does_not_bridge_gaps():
    dates = [1, 2, 3, 4, 5, 6]
    flags = [True, True, False, False, True, False]
    assert contiguous_spans(dates, flags) == [(1, 2), (5, 5)]


def test_identical_series_have_no_discrepancy():
    dates = list(range(50))
    close = np.cumprod(1 + np.full(50, 0.001)) * 100
    assert compare_return_series(dates, close, close) == []


def test_bad_split_factor_shows_as_a_one_day_return_spike():
    # Two series agree everywhere except one source mis-adjusts a split on day 30 -> a single-day
    # return discrepancy at the splice, which must surface as a one-day span.
    dates = list(range(60))
    base = np.cumprod(1 + np.full(60, 0.002)) * 100
    bad = base.copy()
    bad[30:] *= 0.5                       # a 2:1 split applied on only one side from day 30 on
    spans = compare_return_series(dates, base, bad, tol=0.05)
    assert spans == [(30, 30)]            # exactly the splice bar, not a MIN..MAX envelope


def test_daily_log_returns_first_is_nan():
    r = daily_log_returns([100.0, 110.0, 121.0])
    assert np.isnan(r[0])
    assert abs(r[1] - np.log(1.1)) < 1e-12
