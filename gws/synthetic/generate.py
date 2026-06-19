"""Synthetic panel generator for pipeline validation (blueprint §9 / §10).

Produces a deterministic OHLCV panel with KNOWN structure so the detector,
forward-labeling, neutralization, and walk-forward can be validated for leakage
and correctness BEFORE any production data or workstation compute is touched:

  - Planted up-moves (known trough day, magnitude, duration) per ticker.
  - A planted *predictive* feature (`planted_signal`): a pre-move tightness flag
    that is 1 in the 20 days before each planted trough — a genuine pre-move signal
    a correct pipeline should surface.
  - A `null_feature`: i.i.d. noise uncorrelated with moves — a correct pipeline
    should NOT surface it (false-positive check).

`ground_truth` returns the planted moves so tests can score detection recall.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PRE_MOVE_WINDOW = 20


def generate_panel(n_tickers: int = 20, n_days: int = 2520, seed: int = 0,
                   planted_per_ticker: int = 3):
    """Return (panel_df, truth_df).

    panel_df columns: ticker_id, date, open, high, low, close, adjusted_close,
                      volume, planted_signal, null_feature
    truth_df columns: ticker_id, trough_day, magnitude, duration
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2005-01-03", periods=n_days)
    frames = []
    truth = []

    for k in range(n_tickers):
        rets = rng.normal(0.0002, 0.015, n_days)
        signal = np.zeros(n_days)
        starts = np.sort(
            rng.choice(np.arange(252, n_days - 252), size=planted_per_ticker, replace=False)
        )
        for s in starts:
            dur = int(rng.integers(30, 120))
            mag = float(rng.uniform(0.4, 1.5))
            daily = (1 + mag) ** (1 / dur) - 1
            rets[s : s + dur] += daily
            rets[s - PRE_MOVE_WINDOW : s] *= 0.3      # pre-move volatility contraction
            signal[s - PRE_MOVE_WINDOW : s] = 1.0
            truth.append({"ticker_id": k, "trough_day": int(s),
                          "magnitude": mag, "duration": dur})

        close = 100.0 * np.cumprod(1 + rets)
        high = close * (1 + np.abs(rng.normal(0, 0.005, n_days)))
        low = close * (1 - np.abs(rng.normal(0, 0.005, n_days)))
        volume = rng.integers(1_000_000, 5_000_000, n_days).astype(float)
        for s in starts:
            volume[s - PRE_MOVE_WINDOW : s] *= 0.5    # contraction also dampens volume
        null_feature = rng.normal(0, 1, n_days)

        frames.append(pd.DataFrame({
            "ticker_id": k,
            "date": dates,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "adjusted_close": close,
            "volume": volume,
            "planted_signal": signal,
            "null_feature": null_feature,
        }))

    panel = pd.concat(frames, ignore_index=True)
    return panel, pd.DataFrame(truth)
