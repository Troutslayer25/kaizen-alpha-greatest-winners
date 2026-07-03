"""Synthetic panel generator for pipeline validation (blueprint §9 / §10).

Produces a deterministic OHLCV panel with KNOWN structure so the detector,
forward-labeling, neutralization, and walk-forward can be validated for leakage
and correctness BEFORE any production data or workstation compute is touched:

  - Planted up-moves with a minimum spacing so they do not overlap and corrupt
    each other's ground truth.
  - `truth.trough_day` is the ACTUAL price minimum near each planted start (the
    detector's definition of a trough), so detection localization can be scored
    exactly — not the nominal start day.
  - A planted *predictive* feature (`planted_signal`): a pre-move tightness flag
    that is 1 in the days before each planted trough.
  - A `null_feature`: i.i.d. noise uncorrelated with moves (false-positive check).

`ground_truth` is returned alongside the panel so tests can score detection recall
and localization.

Two regimes:
  - CLEAN (`adversarial=False`, default): pristine engineered V-bottoms. Used to score
    detection localization and prove leakage-freedom — you need exact ground truth, which
    requires clean paths.
  - ADVERSARIAL (`adversarial=True`): the clean structure plus injected chaos — flash-crash
    artifacts, erratic volume spikes, choppy false-breakout bottoms, and the planted signal
    occasionally obscured by liquidity shocks. Used to STRESS-TEST that the detector still
    locates moves and that A3 still isolates the planted signal from noise under messy,
    real-market-like conditions. Ground-truth troughs are RE-DERIVED after injection, so the
    oracle stays scoreable even when the paths are violent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PRE_MOVE_WINDOW = 20
DECLINE_DAYS = 30            # decline into each planted trough
PRE_MOVE_DECLINE = 0.25     # size of that decline (> reversal threshold, so it closes the prior leg)
MIN_START_GAP = 200         # > decline + max duration; keeps planted moves non-overlapping
TROUGH_SEARCH = (35, 5)     # search window (before, after) the nominal start for the true min


def _sample_starts(rng, lo, hi, k, min_gap):
    starts: list[int] = []
    attempts = 0
    while len(starts) < k and attempts < 10_000:
        c = int(rng.integers(lo, hi))
        if all(abs(c - s) >= min_gap for s in starts):
            starts.append(c)
        attempts += 1
    return sorted(starts)


def _inject_chaos(rng, rets, volume, signal, plan, n_days):
    """Add adversarial, market-like chaos to one ticker's returns/volume IN PLACE.

    - Flash crashes: a sharp 1-2 day drop + partial recovery, placed AWAY from planted
      pre-move windows so they don't destroy a planted trough.
    - Erratic volume spikes: random days x large multiplier, uncorrelated with anything.
    - False-breakout bottoms: a brief extra dip just BEFORE a planted trough (a shakeout
      that breaks support then reverses) — trough_day is re-derived afterward.
    - Signal obscured: on a fraction of moves, re-inflate the pre-move volatility so the
      planted contraction is partly masked (the LABEL stays; only the feature is noisier).
    """
    move_windows = [(s - DECLINE_DAYS, s + 5) for s, _, _ in plan]

    def _in_move_window(i):
        return any(a <= i <= b for a, b in move_windows)

    # flash crashes (a few, away from planted moves)
    for _ in range(rng.integers(2, 5)):
        i = int(rng.integers(60, n_days - 5))
        if _in_move_window(i):
            continue
        drop = float(rng.uniform(0.10, 0.20))
        rets[i] -= drop
        rets[i + 1] += drop * float(rng.uniform(0.4, 0.8))   # partial snap-back

    # erratic volume spikes
    for _ in range(rng.integers(8, 16)):
        i = int(rng.integers(0, n_days))
        volume[i] *= float(rng.uniform(3.0, 8.0))

    # overnight gaps (up AND down): a one-bar jump with no surrounding drift, away from planted
    # moves — stresses ATR / true-range (the |high - prev_close| term) and any gap-sensitive
    # feature, whose hard cases a gap-free synthetic never exercises.
    for _ in range(rng.integers(4, 9)):
        i = int(rng.integers(30, n_days - 2))
        if _in_move_window(i):
            continue
        rets[i] += float(rng.choice([-1.0, 1.0])) * float(rng.uniform(0.05, 0.12))

    # per-move adversarial behavior
    for s, _, _ in plan:
        if rng.random() < 0.5:                               # false-breakout shakeout before trough
            j = max(1, s - int(rng.integers(2, 8)))
            rets[j] -= float(rng.uniform(0.04, 0.09))
            rets[min(j + 1, n_days - 1)] += float(rng.uniform(0.02, 0.05))
        if rng.random() < 0.4:                               # obscure the contraction signal
            w0 = max(0, s - PRE_MOVE_WINDOW)
            rets[w0:s] += rng.normal(0, 0.02, s - w0)


def generate_panel(n_tickers: int = 20, n_days: int = 2520, seed: int = 0,
                   planted_per_ticker: int = 3, adversarial: bool = False):
    """Return (panel_df, truth_df).

    panel_df columns: ticker_id, date, open, high, low, close, adjusted_close,
                      volume, planted_signal, null_feature
    truth_df columns: ticker_id, trough_day (actual price minimum), magnitude, duration

    `adversarial=True` injects flash crashes, volume spikes, false-breakout bottoms, and
    signal obscuration; ground-truth troughs are re-derived from the corrupted close so the
    panel stays scoreable.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2005-01-03", periods=n_days)
    frames = []
    truth = []

    for k in range(n_tickers):
        base_vol = 0.006 if not adversarial else 0.010
        rets = rng.normal(0.0, base_vol, n_days)      # low base noise: only planted moves are significant
        signal = np.zeros(n_days)
        starts = _sample_starts(rng, 252, n_days - 252, planted_per_ticker, MIN_START_GAP)
        daily_dn = (1 - PRE_MOVE_DECLINE) ** (1 / DECLINE_DAYS) - 1
        plan = []
        for s in starts:
            dur = int(rng.integers(40, 110))
            mag = float(rng.uniform(0.5, 1.5))
            daily_up = (1 + mag) ** (1 / dur) - 1
            rets[s - PRE_MOVE_WINDOW : s] *= 0.3      # pre-move volatility contraction (planted signal)
            rets[s - DECLINE_DAYS : s] += daily_dn    # decline into a clear trough; closes the prior leg
            rets[s : s + dur] += daily_up
            signal[s - PRE_MOVE_WINDOW : s] = 1.0
            plan.append((s, mag, dur))

        volume = rng.integers(1_000_000, 5_000_000, n_days).astype(float)
        for s, _, _ in plan:
            volume[s - PRE_MOVE_WINDOW : s] *= 0.5    # contraction also dampens volume

        if adversarial:
            _inject_chaos(rng, rets, volume, signal, plan, n_days)

        close = 100.0 * np.cumprod(1 + rets)
        high = close * (1 + np.abs(rng.normal(0, 0.005, n_days)))
        low = close * (1 - np.abs(rng.normal(0, 0.005, n_days)))
        null_feature = rng.normal(0, 1, n_days)

        for s, mag, dur in plan:
            w0 = max(0, s - TROUGH_SEARCH[0])
            w1 = min(n_days, s + TROUGH_SEARCH[1])
            trough_day = w0 + int(np.argmin(close[w0:w1]))   # re-derived from (possibly corrupted) close
            truth.append({"ticker_id": k, "trough_day": trough_day,
                          "magnitude": mag, "duration": dur})

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
