"""Contiguous-span helper for data-quality flags (review, lineage aspect).

Both the FMP<->Norgate completeness audit and the data-quality sweep must record CONTIGUOUS
runs of bad bars, not a single MIN(date)->MAX(date) envelope. A MIN/MAX collapse over
non-contiguous corruption (the normal case) marks every clean bar between two bad stretches as
excluded — over-exclusion that silently thins the universe. `contiguous_spans` turns a boolean
mask over dated rows into the list of (from_date, to_date) runs where the mask is True."""
from __future__ import annotations


def contiguous_spans(dates, flags):
    """dates: sorted sequence; flags: same-length booleans. Returns [(from_date, to_date), ...],
    one per maximal run of True."""
    spans = []
    start = None
    prev = None
    for d, f in zip(dates, flags):
        if f and start is None:
            start = d
        elif not f and start is not None:
            spans.append((start, prev))
            start = None
        prev = d
    if start is not None:
        spans.append((start, prev))
    return spans
