"""Framework-neutral price/volatility math (provenance Tier A).

Pure NumPy. No analytical/parameter choices baked in beyond the explicit
arguments. Re-implemented clean for the study rather than imported from the
production pipeline, so there is nothing to strip and one-time attestation
suffices (KA_AUDITOR_PROMPTS_V6.md §1A).
"""
from __future__ import annotations

import numpy as np


def true_range(high, low, close) -> np.ndarray:
    high = np.asarray(high, float)
    low = np.asarray(low, float)
    close = np.asarray(close, float)
    prev_close = np.empty_like(close)
    prev_close[0] = close[0]
    prev_close[1:] = close[:-1]
    return np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)),
    )


def wilder_atr(high, low, close, period: int = 14) -> np.ndarray:
    """Wilder's ATR, seeded with the SMA of the first `period` true ranges.

    Matches the production step_03 convention. Returns an array the same length
    as the input with NaN for the first `period-1` bars.
    """
    tr = true_range(high, low, close)
    atr = np.full(len(tr), np.nan)
    if len(tr) < period:
        return atr
    atr[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def sma(values, period: int) -> np.ndarray:
    values = np.asarray(values, float)
    out = np.full(len(values), np.nan)
    if len(values) < period:
        return out
    cs = np.cumsum(values)
    out[period - 1] = cs[period - 1] / period
    out[period:] = (cs[period:] - cs[:-period]) / period
    return out


def ema(values, period: int) -> np.ndarray:
    """EMA seeded with the SMA of the first `period` values (step_03 convention)."""
    values = np.asarray(values, float)
    out = np.full(len(values), np.nan)
    if len(values) < period:
        return out
    alpha = 2.0 / (period + 1.0)
    out[period - 1] = values[:period].mean()
    for i in range(period, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out
