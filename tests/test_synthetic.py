import numpy as np

from gws.synthetic.generate import generate_panel
from gws.phase_a1.trough_detector import detect_moves


def test_generator_is_deterministic_and_shaped():
    p1, t1 = generate_panel(n_tickers=3, n_days=1500, seed=1, planted_per_ticker=2)
    p2, t2 = generate_panel(n_tickers=3, n_days=1500, seed=1, planted_per_ticker=2)
    assert len(p1) == 3 * 1500
    assert p1["close"].equals(p2["close"])           # deterministic under seed
    assert len(t1) == 6                              # 3 tickers x 2 planted moves
    assert {"planted_signal", "null_feature"}.issubset(p1.columns)


def test_detector_finds_planted_move_on_synthetic():
    panel, truth = generate_panel(n_tickers=5, n_days=2000, seed=7, planted_per_ticker=3)
    found_any = False
    for tk in panel["ticker_id"].unique():
        sub = panel[panel["ticker_id"] == tk]
        moves = detect_moves(sub["high"].to_numpy(), sub["low"].to_numpy(),
                             sub["close"].to_numpy())
        if moves and max(m.trough_gain_pct for m in moves) > 0.20:
            found_any = True
            break
    assert found_any, "detector should recover at least one planted up-move"
