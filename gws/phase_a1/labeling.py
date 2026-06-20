"""Forward-labeling for the production classifier (`setup_labels`, Phase A1/A3).

The production dataset is an INDEPENDENT sampling frame (blueprint T1): (ticker, date)
points sampled across the universe, labeled positive if a confirmed move's trough
falls within the next K trading days. Features are measured at the point's own date
(at or before the trough) — matching deployment, where no one knows they are standing
at a trough. This is NOT derived from matched_controls.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_setup_labels(moves_by_ticker: dict, n_days: int, forward_window_k: int, *,
                       sample_every: int = 5, min_index: int = 210,
                       max_index: int | None = None) -> pd.DataFrame:
    """Sample (ticker, as_of_index) points at a fixed cadence and label them.

    A point at index i is positive if some confirmed trough lies in (i, i + K]; its
    lead_time_days is (trough - i). Returns columns:
    ticker_id, as_of_index, label, forward_window_k, lead_time_days, linked_trough_index.

    Multi-scale note: with the MFE detector, the SAME trough can appear at several scales.
    Pass `moves_by_ticker` containing a SINGLE scale (the pre-committed primary scale), or
    dedup troughs across scales before calling, so a trough is not labeled repeatedly.
    """
    rows = []
    hi = n_days if max_index is None else min(max_index, n_days)
    for tk, moves in moves_by_ticker.items():
        troughs = np.array(sorted(m.trough_idx for m in moves), dtype=int)
        for i in range(min_index, hi):
            if (i - min_index) % sample_every != 0:
                continue
            lead, linked = None, None
            if troughs.size:
                ahead = troughs[(troughs > i) & (troughs <= i + forward_window_k)]
                if ahead.size:
                    linked = int(ahead[0])
                    lead = linked - i
            rows.append({
                "ticker_id": tk,
                "as_of_index": i,
                "label": lead is not None,
                "forward_window_k": forward_window_k,
                "lead_time_days": lead,
                "linked_trough_index": linked,
            })
    return pd.DataFrame(rows)
