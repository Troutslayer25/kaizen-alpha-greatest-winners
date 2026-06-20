"""Two-step ATR-confirmed trough / up-move detector (Phase A1).

NOTE: superseded as the canonical detector by the threshold-free multi-scale MFE detector
(gws/phase_a1/move_detector_mfe.py). Retained as a reference / cross-check baseline — its
fixed confirmation floor (3xATR + 10%) is exactly the detection floor the MFE design
removes, so it is NOT used for the primary continuous move population. Kept for the
absolute/volatility cross-check comparison (scripts/compare_move_detectors.py).


Framework-neutral price-geometry detector: it makes no commitment to any pattern
(base breakout, etc.). A trough is a volatility-confirmed local minimum on
adjusted close; a move runs from that trough to the subsequent peak and is closed
when price corrects from its running peak by the pre-committed reversal threshold.

The forward travel used to *confirm* a trough and to *fix* the peak is used only
to define move boundaries. It never enters the feature set — features are
extracted as of `start_date` (the trough) by Phase A2. (V10 Part V; auditor T7.)

Warm-up: ATR is undefined for the first `atr_period-1` bars, so a candidate
trough there cannot be confirmed (the seek loop skips NaN ATR). This is the
correct behaviour — confirming an early trough would require ATR computed from
post-trough bars (look-ahead). In production the 252-day minimum-history rule
guarantees troughs never fall in the warm-up region.

The detector is ticker-agnostic and returns integer indices; the caller maps
indices to dates and attaches ticker_id when writing to gws.moves.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gws.common.indicators import wilder_atr


@dataclass
class Move:
    trough_idx: int
    peak_idx: int
    trough_gain_pct: float          # peak/trough - 1
    duration_days: int              # peak_idx - trough_idx
    max_intra_drawdown: float       # max close drawdown from running peak within the move
    smoothness: float               # path efficiency: net move / sum |daily change|, in [0,1]
    is_open: bool                   # True if the move never resolved before series end
    detection_system: str           # 'atr_swing' | 'absolute_return'
    reversal_threshold: float       # the threshold this move was segmented at


def _record(close, trough_idx, peak_idx, is_open, detection_system, reversal_threshold) -> Move:
    seg = close[trough_idx : peak_idx + 1]
    trough = seg[0]
    peak = close[peak_idx]
    gain = peak / trough - 1.0
    running_max = np.maximum.accumulate(seg)
    with np.errstate(divide="ignore", invalid="ignore"):
        dd = np.where(running_max > 0, (running_max - seg) / running_max, np.nan)
    max_dd = float(np.nanmax(dd)) if np.isfinite(dd).any() else float("nan")
    net = abs(peak - trough)
    path = float(np.abs(np.diff(seg)).sum())
    smoothness = net / path if path > 0 else 0.0
    return Move(
        trough_idx=int(trough_idx),
        peak_idx=int(peak_idx),
        trough_gain_pct=float(gain),
        duration_days=int(peak_idx - trough_idx),
        max_intra_drawdown=max_dd,
        smoothness=float(smoothness),
        is_open=is_open,
        detection_system=detection_system,
        reversal_threshold=float(reversal_threshold),
    )


def detect_moves(
    high,
    low,
    close,
    *,
    atr_period: int = 21,
    atr_mult: float = 3.0,
    min_abs_gain: float = 0.10,
    min_duration: int = 10,
    reversal_threshold: float = 0.20,
    detection_system: str = "atr_swing",
) -> list[Move]:
    """Detect significant up-moves via two-step trough confirmation + reversal segmentation.

    Confirmation: a candidate trough (lowest close since the last resolved peak) is
    confirmed once price rises from it by BOTH at least `atr_mult` * ATR(atr_period)
    measured at the candidate low AND at least `min_abs_gain` in percent terms.

    Segmentation: once in a move, the running peak is tracked; a correction of
    `reversal_threshold` from the running peak closes the move at that peak and a
    new candidate-trough search begins.

    Moves shorter than `min_duration` trading days are discarded.
    """
    high = np.asarray(high, float)
    low = np.asarray(low, float)
    close = np.asarray(close, float)
    n = len(close)
    atr = wilder_atr(high, low, close, atr_period)

    moves: list[Move] = []
    state = "seek"
    cand_low = close[0]
    cand_low_idx = 0
    trough_idx = 0
    running_peak = close[0]
    running_peak_idx = 0

    for i in range(1, n):
        if state == "seek":
            if close[i] < cand_low:
                cand_low = close[i]
                cand_low_idx = i
                continue
            atr_at_low = atr[cand_low_idx]
            if np.isnan(atr_at_low) or cand_low <= 0:
                continue
            rise = close[i] - cand_low
            if rise >= atr_mult * atr_at_low and (close[i] / cand_low - 1.0) >= min_abs_gain:
                state = "in_move"
                trough_idx = cand_low_idx
                seg = close[trough_idx : i + 1]
                running_peak_idx = trough_idx + int(np.argmax(seg))
                running_peak = close[running_peak_idx]
        else:  # in_move
            if close[i] > running_peak:
                running_peak = close[i]
                running_peak_idx = i
                continue
            if (running_peak - close[i]) / running_peak >= reversal_threshold:
                if running_peak_idx - trough_idx >= min_duration:
                    moves.append(_record(close, trough_idx, running_peak_idx, False,
                                         detection_system, reversal_threshold))
                state = "seek"
                cand_low = close[i]
                cand_low_idx = i

    if state == "in_move" and running_peak_idx - trough_idx >= min_duration:
        moves.append(_record(close, trough_idx, running_peak_idx, True,
                             detection_system, reversal_threshold))

    return moves
