"""Persistence: MoveMFE + characterization -> queryable gws.moves row (pure core)."""
import datetime as dt
import json
import types

import numpy as np

from gws.phase_a1.move_characterization import characterize_move, inception_context
from gws.phase_a1.persist_moves import build_rows, move_to_row


def _move(trough=300, peak=390, scale="trail_6"):
    return types.SimpleNamespace(trough_idx=trough, peak_idx=peak, magnitude=0.9,
                                 duration_days=peak - trough, mae=0.03, smoothness=0.6,
                                 early_smoothness=0.4, drawdown_timing=0.2, trail_atr=6.0,
                                 scale=scale, is_open=False)


def _dates(n=420):
    base = dt.date(2005, 1, 3)
    return [base + dt.timedelta(days=i) for i in range(n)]


def test_move_to_row_maps_indices_to_dates_and_bags_json():
    m = _move()
    dates = _dates()
    desc = {"num_pullbacks": 2, "largest_pullback": 0.08, "max_intra_drawdown": 0.08,
            "bad": float("nan")}
    inc = {"incept_above_sma200": 1.0, "incept_rsi_14": 41.0}
    row = move_to_row(m, 42, lambda i: dates[i], desc, inc, is_primary_scale=True)
    assert row["ticker_id"] == 42
    assert row["start_date"] == dates[300] and row["peak_date"] == dates[390]
    assert row["detection_system"] == "mfe" and row["is_primary_scale"] is True
    d = json.loads(row["descriptors"])
    assert d["num_pullbacks"] == 2 and d["bad"] is None          # NaN -> JSON null (valid JSONB)
    assert json.loads(row["inception"])["incept_above_sma200"] == 1.0


def test_build_rows_characterizes_and_flags_primary_scale():
    rng = np.random.default_rng(0)
    n = 420
    close = np.abs(np.concatenate([np.linspace(100, 80, 301), np.linspace(80, 160, 90),
                                   np.linspace(160, 150, 29)]) + rng.normal(0, 0.2, n))
    dates = _dates(n)
    moves = [_move(scale="trail_6"), _move(trough=305, peak=360, scale="trail_2")]
    rows = build_rows(moves, 7, dates, close, close * 1.01, close * 0.99,
                      volume=rng.integers(1e6, 5e6, n).astype(float),
                      primary_scale="trail_6")
    assert len(rows) == 2
    assert rows[0]["is_primary_scale"] is True and rows[1]["is_primary_scale"] is False
    # the descriptor + inception bags are populated and JSON-valid
    assert "num_pullbacks" in json.loads(rows[0]["descriptors"])
    assert any(k.startswith("incept_") for k in json.loads(rows[0]["inception"]))
