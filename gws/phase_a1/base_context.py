"""PIT base / stage context at the trough (review MC-2) — the taxonomy completer.

`inception_context`'s original fields say where price sits vs its MAs; these say what KIND of
structure preceded the trough, so the catalog can tell a flat-base Stage-2 launch from a V-shaped
crash recovery from a high-tight flag — the distinctions a growth trader queries by. Every field is
a pure function of data <= trough (bias-free), so it merges into the inception bag and is
future-invariance tested alongside the rest.
"""
from __future__ import annotations

import numpy as np

BASE_FIELDS = ("incept_days_since_252high", "incept_days_since_252low", "incept_prior_leg_gain",
               "incept_vcp_ratio_63", "incept_tightness_63", "incept_stage", "incept_ma_stack")


def base_context(close, i, high=None, low=None) -> dict:
    """PIT base/stage descriptors at index i (uses only data <= i)."""
    close = np.asarray(close, float)
    hi = close if high is None else np.asarray(high, float)
    lo = close if low is None else np.asarray(low, float)
    out = {k: np.nan for k in BASE_FIELDS}

    if i - 251 >= 0:
        hw, lw = hi[i - 251:i + 1], lo[i - 251:i + 1]
        h_at = int(np.argmax(hw)); l_at = int(np.argmin(lw))
        out["incept_days_since_252high"] = float((len(hw) - 1) - h_at)
        out["incept_days_since_252low"] = float((len(lw) - 1) - l_at)
        pre = lw[:h_at + 1]                              # the low that preceded the 252-high
        if pre.size and pre.min() > 0:
            out["incept_prior_leg_gain"] = float(hw[h_at] / pre.min() - 1.0)

    if i - 62 >= 0:
        h63, l63 = hi[i - 62:i + 1], lo[i - 62:i + 1]
        rng = h63 - l63
        recent, earlier = rng[-21:].mean(), rng[-42:-21].mean()
        out["incept_vcp_ratio_63"] = float(recent / earlier) if earlier > 0 else np.nan
        med = float(np.median(rng))
        out["incept_tightness_63"] = float(np.mean(rng < med)) if med > 0 else np.nan

    def _sma(p):
        return close[i - p + 1:i + 1].mean() if i - p + 1 >= 0 else np.nan
    s50, s150, s200 = _sma(50), _sma(150), _sma(200)
    s200_prior = close[i - 220:i - 20].mean() if i - 220 >= 0 else np.nan   # sma200 ~21 bars ago
    if s200 == s200 and s200_prior == s200_prior:
        rising, above = s200 > s200_prior, close[i] > s200
        out["incept_stage"] = float(2 if (above and rising) else 3 if above else 4 if not rising else 1)
    if all(x == x for x in (s50, s150, s200)):
        out["incept_ma_stack"] = float(s50 > s150 > s200)   # proper trend-template stack order
    return out
