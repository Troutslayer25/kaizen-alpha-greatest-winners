"""Threshold-free, multi-scale move detector (prototype).

Design settled with Scott (June 2026), in response to the "2.5-ATR move is invisible"
critique of the ATR-swing detector:

- **No confirmation floor.** Every local low seeds a move; magnitude is *measured*, not
  gated. The move population is a continuous distribution from tiny to huge — nothing is
  invisible. "Significant" is later defined as a percentile of that distribution.
- **Non-gating drawdown, recorded.** A small early dip below the start does not kill the
  move; the maximum adverse excursion (MAE) below the start is recorded as a property.
- **End = volatility-scaled trailing stop from the PEAK, not a round-trip.** The move tops
  when price closes more than `trail_atr * ATR` below its highest close. Early on, when the
  peak is still near the start, this same band is what tolerates the early drawdown — one
  parameter does both jobs.
- **Multi-scale.** Run at several `trail_atr` widths; a tight stop carves out short swing
  legs, a loose stop captures the big arc. Each move is tagged with its scale, so nested
  short moves inside long trends are kept rather than absorbed.

`trail_atr` is the one dial (the scale). It is ATR-scaled (no fixed-% bias) and is meant to
be pre-committed and swept. The peak/forward travel defines move boundaries only — never
features (Phase A2 extracts features as of the trough).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gws.common.indicators import wilder_atr


@dataclass
class MoveMFE:
    trough_idx: int
    peak_idx: int
    magnitude: float          # peak/trough - 1
    duration_days: int        # peak_idx - trough_idx
    mae: float                # max adverse excursion below the start (fraction >= 0), recorded
    smoothness: float         # net / sum|daily change| in [0,1]; low = wild path
    trail_atr: float          # the scale this move was detected at
    scale: str
    is_open: bool


def _record(close, trough_idx, peak_idx, trail_atr, scale, is_open) -> MoveMFE:
    seg = close[trough_idx : peak_idx + 1]
    s = seg[0]
    pk = close[peak_idx]
    mae = float(max(0.0, (s - seg.min()) / s)) if s > 0 else float("nan")
    net = pk - s
    path = float(np.abs(np.diff(seg)).sum())
    smoothness = net / path if path > 0 else 0.0
    return MoveMFE(
        trough_idx=int(trough_idx), peak_idx=int(peak_idx),
        magnitude=float(pk / s - 1.0), duration_days=int(peak_idx - trough_idx),
        mae=mae, smoothness=float(smoothness), trail_atr=float(trail_atr),
        scale=scale, is_open=is_open,
    )


def detect_moves_mfe(high, low, close, *, atr_period: int = 21, trail_atr: float = 3.0,
                     min_duration: int = 1, scale: str | None = None) -> list[MoveMFE]:
    """Detect moves at a single scale (`trail_atr`). See module docstring."""
    close = np.asarray(close, float)
    atr = wilder_atr(np.asarray(high, float), np.asarray(low, float), close, atr_period)
    scale = scale or f"trail_{trail_atr:g}"
    n = len(close)
    moves: list[MoveMFE] = []

    start_idx = 0
    peak_idx = 0
    peak = close[0]
    for i in range(1, n):
        s = close[start_idx]
        if peak <= s:                                   # not risen yet — still seeking the trough
            if close[i] < s:
                start_idx = i; peak = close[i]; peak_idx = i
            elif close[i] > peak:
                peak = close[i]; peak_idx = i
            continue
        if close[i] > peak:                             # new high — extend the move
            peak = close[i]; peak_idx = i
            continue
        a = atr[i]
        if np.isnan(a):                                 # warm-up: cannot evaluate the stop, hold
            continue
        if close[i] < peak - trail_atr * a:             # trailing stop hit — move tops at peak
            if peak_idx - start_idx >= min_duration and peak > s:
                moves.append(_record(close, start_idx, peak_idx, trail_atr, scale, False))
            start_idx = i; peak = close[i]; peak_idx = i

    if peak > close[start_idx] and peak_idx - start_idx >= min_duration:
        moves.append(_record(close, start_idx, peak_idx, trail_atr, scale, True))
    return moves


def detect_moves_multiscale(high, low, close, *, scales=(2.0, 6.0, 15.0),
                            atr_period: int = 21, min_duration: int = 1) -> dict:
    """Run the detector at several trailing-stop widths. Returns {trail_atr: [MoveMFE]}.
    Tight scales carve out swing legs; loose scales capture the big arc."""
    return {
        k: detect_moves_mfe(high, low, close, atr_period=atr_period, trail_atr=k,
                            min_duration=min_duration, scale=f"trail_{k:g}")
        for k in scales
    }
