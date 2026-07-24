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

# Pre-committed required earliest-membership depth per index (review m-7). Step-0 must ASSERT
# the sampled earliest membership reaches at least this date, not merely that the watchlist is
# non-empty — a Russell series that only starts in the 2000s would otherwise pass GO while the
# study leans on deep history. Confirm/adjust against the installed norgatedata version; a miss
# is a documented NO-GO for that index, not a warning.
# AMENDED 2026-07-24 (Scott, Step-0 run on KA-Workstation, norgatedata 1.0.77): original values
# predated vendor/index inception. Evidence: sp600 index launched 1994-10-28 (Norgate has it from
# inception); Russell constituent flags begin exactly 1990-07-03 for GE/XOM/IBM (series start,
# July 1990 reconstitution); NDX-100 flags begin 1993-10-01 for AAPL/MSFT/INTC (members since the
# 1980s → vendor series start, not membership start). All 7 kept; pre-1990 eras are covered by the
# pre-committed all-listed-equity deep-era universe rule, not the index gate. Ingest must treat
# dates BEFORE these starts as UNKNOWN membership, never non-member.
REQUIRED_START = {
    "sp500": "1990-01-01", "sp400": "1994-01-01", "sp600": "1994-10-28",
    "r1000": "1990-07-03", "r2000": "1990-07-03", "r3000": "1990-07-03",
    "ndx100": "1993-10-01",
}


def meets_required_start(earliest, required) -> bool:
    """True iff `earliest` (str/date or None) is on/before the `required` date string."""
    if earliest is None:
        return False
    return str(earliest)[:10] <= required


def _earliest_membership_date(symbol: str, index_label: str):
    """Earliest date this symbol shows as a constituent of index_label, or None."""
    import norgatedata  # ka-runner only
    df = norgatedata.index_constituent_timeseries(
        symbol, index_label, timeseriesformat="pandas-dataframe")
    if df is None or df.empty:
        return None
    member = df[df["Index Constituent"] == 1]
    return None if member.empty else member.index.min()


def coverage_for_index(index_label: str, watchlist: str) -> dict:
    import norgatedata  # ka-runner only
    try:
        members = norgatedata.watchlist_symbols(watchlist)
    except Exception as e:  # noqa: BLE001 — diagnostic script, surface any failure
        return {"available": False, "error": f"watchlist '{watchlist}': {e}"}
    if not members:
        return {"available": False, "error": f"watchlist '{watchlist}' empty"}

    # Sample BOTH current and delisted members explicitly (review m-7). Norgate decorates
    # delisted symbols as 'SYMBOL-YYYYMM'; sampling only the head of the list (mostly current
    # members) would estimate a too-recent earliest date and never exercise the survivorship-
    # critical names.
    delisted = [s for s in members if "-" in s][:25]
    current = [s for s in members if "-" not in s][:25]
    sample = current + delisted

    earliest = None
    sampled = n_delisted = 0
    for sym in sample:
        try:
            d = _earliest_membership_date(sym, index_label)
        except Exception:  # noqa: BLE001
            continue
        sampled += 1
        n_delisted += ("-" in sym)
        if d is not None and (earliest is None or d < earliest):
            earliest = d
    return {
        "available": True,
        "n_ever_members": len(members),
        "n_sampled": sampled,
        "n_delisted_sampled": n_delisted,
        "earliest_membership_sampled": str(earliest) if earliest is not None else None,
    }


def main() -> int:
    print(f"{'index':8} {'avail':6} {'ever':>7} {'sampl':>6} {'delist':>6} "
          f"{'earliest':>12} {'req':>12} depth")
    ok = True
    for name, (label, watchlist) in TARGET_INDEXES.items():
        cov = coverage_for_index(label, watchlist)
        if not cov.get("available"):
            ok = False
            print(f"{name:8} {'NO':6}  -- error: {cov.get('error')}")
            continue
        required = REQUIRED_START.get(name, "9999-99-99")
        deep_ok = meets_required_start(cov["earliest_membership_sampled"], required)
        has_delisted = cov.get("n_delisted_sampled", 0) > 0
        row_ok = deep_ok and has_delisted
        ok = ok and row_ok
        print(f"{name:8} {'YES':6} {cov['n_ever_members']:>7} {cov['n_sampled']:>6} "
              f"{cov.get('n_delisted_sampled', 0):>6} "
              f"{str(cov['earliest_membership_sampled'])[:10]:>12} {required:>12} "
              f"{'OK' if row_ok else 'SHORT' if not deep_ok else 'NO-DELISTED'}")
    print("\nGO" if ok else "\nNO-GO — an index fails required depth or exposes no delisted "
          "members. Drop it with documented rationale before Step 1 (Scott).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
