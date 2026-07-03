"""True lockbox enforcement (review C-1) — the #7 researcher-DoF control, made mechanical.

The lockbox is a final out-of-sample era that is NEVER examined until the very end, bounding the
researcher degrees of freedom that FDR cannot reach. It was folklore (prose, no date, no code);
this makes it machinery: pipeline entry points refuse to emit rows dated on/after LOCKBOX_START
unless an explicit `unlock=True` is passed, and the boundary is committed in
phases/LOCKBOX_PRECOMMIT.md.

LOCKBOX_START is a RECOMMENDED default (Scott ratifies in the precommit). It must be set BEFORE the
Gate 0.5 pilot and never moved afterward (moving it is itself a forking path)."""
from __future__ import annotations

import datetime as _dt

# RECOMMENDED boundary — ratify in phases/LOCKBOX_PRECOMMIT.md before Gate 0.5. Everything on/after
# this date is the sealed holdout. (~ final years of the modern FMP era; a large fraction of the
# regimes the invariance thesis cares about sit before it.)
LOCKBOX_START = _dt.date(2022, 1, 1)


def in_lockbox(date, *, start: _dt.date = LOCKBOX_START) -> bool:
    """True if `date` is inside the sealed holdout (on/after the boundary)."""
    d = date if isinstance(date, _dt.date) else _dt.date.fromisoformat(str(date)[:10])
    return d >= start


def assert_not_in_lockbox(dates, *, unlock: bool = False, start: _dt.date = LOCKBOX_START) -> None:
    """Raise if any date is in the lockbox, unless `unlock=True`. Call at every pipeline entry that
    emits rows (detection, eligibility, feature extraction) so the holdout cannot be examined by
    accident. `unlock=True` is the single, auditable act of opening the holdout at the very end."""
    if unlock:
        return
    for d in dates:
        if in_lockbox(d, start=start):
            raise PermissionError(
                f"date {d} is inside the sealed lockbox (>= {start}); the final holdout must not be "
                f"examined before the lockbox is opened. Pass unlock=True only at the terminal step.")


def drop_lockbox(dates, *arrays, unlock: bool = False, start: _dt.date = LOCKBOX_START):
    """Convenience: truncate `dates` (and any parallel arrays) to the pre-lockbox span. Returns
    (dates, *arrays) unchanged if unlock=True."""
    if unlock:
        return (list(dates), *arrays)
    keep = [i for i, d in enumerate(dates) if not in_lockbox(d, start=start)]
    dates2 = [dates[i] for i in keep]
    out = tuple([a[i] for i in keep] if isinstance(a, list) else a[keep] for a in arrays)
    return (dates2, *out)
