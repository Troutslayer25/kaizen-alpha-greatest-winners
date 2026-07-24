"""Regression: detect_moves_for_ticker must scale RAW high/low into adjusted space.

Motivating failure (found 2026-07-24, pre-pilot): both price tables store raw H/L next to
adjusted_close; pairing them unscaled hands the detector a pre-split bar whose 'high' is a
split-ratio away from its close, poisoning Wilder ATR and the trailing stop for every name
with a split — exactly the phantom-move class (Risk #4) Gate 0.5 exists to catch."""
import datetime as dt

import numpy as np

from gws.phase_a1.detect_driver import detect_moves_for_ticker


class _Cur:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Conn:
    """Serves the three queries the loader makes: whole-entity exclusions (none),
    exception spans (none), and the bar series with a 1:10 reverse split mid-way."""

    def __init__(self):
        n = 300
        base = dt.date(2015, 1, 5)
        adj = 100.0 * 1.001 ** np.arange(n)          # smooth adjusted series, no real move
        split_at = 150
        factor = np.where(np.arange(n) < split_at, 10.0, 1.0)
        raw = adj / factor
        self.rows = [{
            "date": base + dt.timedelta(days=i),
            "high": raw[i] * 1.01, "low": raw[i] * 0.99,
            "raw_close": raw[i], "close": adj[i], "volume": 1e6,
        } for i in range(n)]

    def execute(self, sql, params=None):
        if "date_from IS NULL" in sql:
            return _Cur([])
        if "date_from IS NOT NULL" in sql:
            return _Cur([])
        return _Cur(self.rows)


def test_high_low_are_scaled_into_adjusted_space():
    dates, close, high, low, volume, by_scale = detect_moves_for_ticker(
        _Conn(), 42, source="norgate")
    assert len(dates) == 300
    # geometry preserved bar-by-bar in adjusted space: high ~ close*1.01, low ~ close*0.99
    assert np.allclose(high / close, 1.01, atol=1e-9)
    assert np.allclose(low / close, 0.99, atol=1e-9)
    # the split bar must not manufacture a move on a flat 0.1%/day series: pre-fix the raw
    # pre-split 'high' sat 10x below adjusted close and ATR exploded at the splice
    for moves in by_scale.values():
        for m in moves:
            assert m.magnitude < 0.5, f"phantom move manufactured at the split: {m}"
