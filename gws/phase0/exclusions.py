"""Consume gws.data_quality_exceptions at move-detection time (review, lineage aspect).

The sweep and completeness audit only TAG bad bars; nothing read the tags, so neither the QC
exclusions nor the "actually-traded-bars" anti-pollution rule was enforceable at the detector.
These primitives make them enforceable:

  tradeable_mask       — False on any bar that is not actually traded (volume <= 0) or falls in
                         a recorded exception span. This is the anti-pollution rule in code.
  forward_fill_excluded — replace untradeable bars with the last good value so the detector sees
                         a flat (zero-return) bar there and cannot seed a phantom trough/move on
                         corrupted or non-traded data, while keeping the series length aligned.

The FORWARD detector-driver calls `tradeable_mask` from the loaded exception spans + volume, then
`forward_fill_excluded` on close/high/low before `detect_moves_mfe`. Pure and testable; DB access
(loading spans) is the caller's job."""
from __future__ import annotations

import numpy as np


def tradeable_mask(dates, volume, exception_spans=()) -> np.ndarray:
    """Boolean mask: True where the bar is genuinely tradeable. False where volume <= 0 or the
    date falls inside any (from_date, to_date) exception span (inclusive)."""
    vol = np.asarray(volume, float)
    mask = np.isfinite(vol) & (vol > 0)
    if exception_spans:
        dates = list(dates)
        for frm, to in exception_spans:
            for i, d in enumerate(dates):
                if frm <= d <= to:
                    mask[i] = False
    return mask


def forward_fill_excluded(values, mask) -> np.ndarray:
    """Return a copy of `values` with every False-mask bar replaced by the last True-mask value,
    so an excluded/untraded bar has a zero return and cannot manufacture a move. Leading excluded
    bars (no prior good value) are left as-is for the caller to drop."""
    v = np.asarray(values, float).copy()
    mask = np.asarray(mask, bool)
    last = np.nan
    for i in range(len(v)):
        if mask[i] and np.isfinite(v[i]):
            last = v[i]
        elif not mask[i] and np.isfinite(last):
            v[i] = last
    return v


def load_exception_spans(conn, ticker_id, *, resolution="excluded"):
    """Load (date_from, date_to) exception spans for one id from gws.data_quality_exceptions."""
    rows = conn.execute(
        "SELECT date_from, date_to FROM gws.data_quality_exceptions "
        "WHERE ticker_id=%s AND resolution=%s AND date_from IS NOT NULL ORDER BY date_from",
        (ticker_id, resolution)).fetchall()
    return [(r["date_from"], r["date_to"]) for r in rows]
