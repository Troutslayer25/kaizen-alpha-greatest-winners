"""Move-significance percentiles WITHOUT full-sample look-ahead (review 2026-07-03 CF-3).

`magnitude_pctile` defines which moves count as "significant" (the positive class). If it
is computed as the percentile of magnitude within the WHOLE 1950-2025 population, a 1975
training-fold label encodes the 2020 move distribution — future information leaks into the
label definition, upstream of any walk-forward split, where purging cannot reach it.

Two PIT-safe assignments; a move's percentile may depend only on moves whose outcome is
known by that move's own decision date (its peak/resolution date):

  frozen_train_pctile  — rank every move against the magnitude ECDF of a FROZEN training
                         block (e.g. the pilot / first fold). Deterministic, simplest to
                         pre-commit; use when one threshold is applied study-wide.
  expanding_pctile     — rank each move against all moves resolved on/before its own
                         decision date. Adapts across eras without peeking forward.

`assign` dispatches and returns the percentile plus a `pctile_basis` provenance string for
the gws.moves.pctile_basis column. There is deliberately no 'full_sample' mode.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MAG = "total_pct_gain"
# The move's DECISION date is when its trailing stop FIRED (resolution), not its peak — magnitude
# and even the peak's finality are unknowable until then (review C-2). Keying on peak_date lets a
# then-open peer's later peak mutate an early move's comparison set across a fold boundary.
DECISION = "resolved_date"


def frozen_train_pctile(df: pd.DataFrame, train_mask, magnitude_col: str = MAG) -> pd.Series:
    """Percentile of each move's magnitude against the frozen training-block ECDF."""
    train = np.sort(df.loc[train_mask, magnitude_col].to_numpy(dtype=float))
    if train.size == 0:
        raise ValueError("frozen_train_pctile: training mask selects no moves")
    all_mags = df[magnitude_col].to_numpy(dtype=float)
    le = np.searchsorted(train, all_mags, side="right")
    return pd.Series(le / train.size, index=df.index)


def expanding_pctile(df: pd.DataFrame, magnitude_col: str = MAG,
                     decision_col: str = DECISION) -> pd.Series:
    """Percentile of each move vs all moves resolved on/before its decision date.

    Same-decision-date moves share eligibility (their outcomes are known together). O(n log n)
    via a Fenwick tree over compressed magnitude ranks."""
    mags = df[magnitude_col].to_numpy(dtype=float)
    dates = df[decision_col].to_numpy()
    n = len(df)
    if n == 0:
        return pd.Series([], dtype=float, index=df.index)

    uniq = np.unique(mags)
    rank = np.searchsorted(uniq, mags) + 1          # 1-based magnitude rank
    U = int(uniq.size)
    tree = np.zeros(U + 1, dtype=np.int64)

    def update(i: int) -> None:
        while i <= U:
            tree[i] += 1
            i += i & (-i)

    def query(i: int) -> int:                        # count of seen magnitudes with rank <= i
        s = 0
        while i > 0:
            s += tree[i]
            i -= i & (-i)
        return s

    order = np.argsort(dates, kind="mergesort")      # stable; groups equal dates together
    od = dates[order]
    out = np.empty(n)
    seen = 0
    i = 0
    while i < n:
        j = i
        while j < n and od[j] == od[i]:
            j += 1
        idxs = order[i:j]
        gsorted = np.sort(mags[idxs])
        denom = seen + idxs.size
        for gi in idxs:
            m = mags[gi]
            le = query(int(rank[gi])) + int(np.searchsorted(gsorted, m, side="right"))
            out[gi] = le / denom
        for gi in idxs:
            update(int(rank[gi]))
        seen += idxs.size
        i = j
    return pd.Series(out, index=df.index)


def assign(df: pd.DataFrame, mode: str, *, train_mask=None, train_end=None,
           magnitude_col: str = MAG, decision_col: str = DECISION):
    """Return (pctile: Series, basis: Series) for the gws.moves writer, aligned to df.index.

    mode='frozen_train' needs train_mask OR train_end (decision_col <= train_end).
    mode='expanding' needs neither. 'full_sample' is intentionally unsupported.

    OPEN moves (unresolved, no resolution date) get NaN percentile and never enter any peer's
    comparison set (review C-2): their magnitude isn't final, so they can't rank or be ranked."""
    resolved = df["is_open"].to_numpy() == False if "is_open" in df.columns \
        else np.ones(len(df), dtype=bool)                                    # noqa: E712
    sub = df[resolved]
    pct = pd.Series(np.nan, index=df.index)
    if mode == "frozen_train":
        if train_mask is None:
            if train_end is None:
                raise ValueError("frozen_train needs train_mask or train_end")
            train_mask = sub[decision_col] <= train_end
        else:
            train_mask = pd.Series(train_mask, index=df.index)[resolved]
        pct.loc[sub.index] = frozen_train_pctile(sub, train_mask, magnitude_col)
        tag = f"frozen_train:{train_end}" if train_end is not None else "frozen_train"
    elif mode == "expanding":
        pct.loc[sub.index] = expanding_pctile(sub, magnitude_col, decision_col)
        tag = "expanding"
    else:
        raise ValueError(f"unsupported significance mode {mode!r} "
                         f"(full-sample percentiles leak the future — CF-3)")
    return pct, pd.Series(tag, index=df.index)
