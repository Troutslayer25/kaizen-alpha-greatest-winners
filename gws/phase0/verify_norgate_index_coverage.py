"""Phase 0, Step 0 — verify Norgate historical index-constituent coverage.

RUNS ON ka-runner (Norgate NDU + Postgres). Cannot be executed on ka-laptop.
Go/no-go for the OQ-1a index set: for each target index, confirm Norgate exposes
historical constituents *including delisted members*, report the earliest membership
date and the count of ever-members. Indexes that lack reliable historical depth are
dropped from the set with documented rationale (Scott reviews).

NOTE (Step-0 validation task): confirm the exact norgatedata index label strings and
"Current & Past" watchlist names against the installed norgatedata version. The labels
below are best-known and may need adjustment — this script exists precisely to surface
that before the ingester (Step 1) is trusted.
"""
from __future__ import annotations

import sys

import norgatedata  # available on ka-runner only

# internal index_name -> (Norgate index label, Norgate "current & past" watchlist name)
TARGET_INDEXES = {
    "sp500":  ("S&P 500", "S&P 500 Current & Past"),
    "sp400":  ("S&P MidCap 400", "S&P MidCap 400 Current & Past"),
    "sp600":  ("S&P SmallCap 600", "S&P SmallCap 600 Current & Past"),
    "r1000":  ("Russell 1000", "Russell 1000 Current & Past"),
    "r2000":  ("Russell 2000", "Russell 2000 Current & Past"),
    "r3000":  ("Russell 3000", "Russell 3000 Current & Past"),
    "ndx100": ("NASDAQ 100", "NASDAQ 100 Current & Past"),
}


def _earliest_membership_date(symbol: str, index_label: str):
    """Earliest date this symbol shows as a constituent of index_label, or None."""
    df = norgatedata.index_constituent_timeseries(
        symbol, index_label, timeseriesformat="pandas-dataframe")
    if df is None or df.empty:
        return None
    member = df[df["Index Constituent"] == 1]
    return None if member.empty else member.index.min()


def coverage_for_index(index_label: str, watchlist: str) -> dict:
    try:
        members = norgatedata.watchlist_symbols(watchlist)
    except Exception as e:  # noqa: BLE001 — diagnostic script, surface any failure
        return {"available": False, "error": f"watchlist '{watchlist}': {e}"}
    if not members:
        return {"available": False, "error": f"watchlist '{watchlist}' empty"}

    earliest = None
    sampled = 0
    for sym in members[: min(len(members), 25)]:  # sample to estimate earliest coverage
        try:
            d = _earliest_membership_date(sym, index_label)
        except Exception:  # noqa: BLE001
            continue
        sampled += 1
        if d is not None and (earliest is None or d < earliest):
            earliest = d
    return {
        "available": True,
        "n_ever_members": len(members),
        "n_sampled": sampled,
        "earliest_membership_sampled": str(earliest) if earliest is not None else None,
    }


def main() -> int:
    print(f"{'index':8} {'avail':6} {'ever':>7} {'sampled':>8}  earliest(sampled)")
    ok = True
    for name, (label, watchlist) in TARGET_INDEXES.items():
        cov = coverage_for_index(label, watchlist)
        if not cov.get("available"):
            ok = False
            print(f"{name:8} {'NO':6}  -- error: {cov.get('error')}")
            continue
        print(f"{name:8} {'YES':6} {cov['n_ever_members']:>7} {cov['n_sampled']:>8}  "
              f"{cov['earliest_membership_sampled']}")
    print("\nGO" if ok else "\nREVIEW REQUIRED — one or more indexes lack coverage; "
          "drop with documented rationale (Scott).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
