"""Phase 0, Step 1 — ingest historical PIT index-constituent membership.

RUNS ON ka-runner (Norgate NDU + Postgres). Cannot be executed on ka-laptop.
Critical-path blocker #1: the production DB has NO index-membership table, and the
entire universe quality filter depends on it. This builds `gws.index_membership` as
PIT from/to intervals from Norgate's constituent timeseries, INCLUDING delisted
members (survivorship-free).

Prerequisite: Step 0 (verify_norgate_index_coverage.py) confirmed the index labels and
coverage. Do not run this until Step 0 is GO.

Symbol -> ticker_id mapping note: Norgate's stable key is `assetid`; symbols can be
recycled. This draft maps by current symbol against the `tickers` table and records
unmapped symbols for review — robust assetid-based mapping is a Step-1 hardening task
flagged for the gate.
"""
from __future__ import annotations

import sys

import norgatedata  # ka-runner only
from ka_lib.db import ka_query, ka_upsert  # ka-runner only

from gws.phase0.verify_norgate_index_coverage import TARGET_INDEXES


def _intervals_from_timeseries(df):
    """Convert a daily 0/1 'Index Constituent' series into (from_date, to_date) runs.
    to_date is None for an interval still open at the end of the series."""
    flag = df["Index Constituent"].to_numpy().astype(int)
    dates = df.index
    intervals = []
    start = None
    for i, v in enumerate(flag):
        if v == 1 and start is None:
            start = dates[i]
        elif v == 0 and start is not None:
            intervals.append((start, dates[i - 1]))
            start = None
    if start is not None:
        intervals.append((start, None))   # still a member at series end
    return intervals


def _symbol_to_ticker_id() -> dict:
    rows = ka_query("SELECT id, symbol FROM tickers")
    return {r["symbol"]: r["id"] for r in rows}


def ingest(dry_run: bool = False) -> dict:
    sym_map = _symbol_to_ticker_id()
    unmapped: set[str] = set()
    n_rows = 0

    for name, (label, watchlist) in TARGET_INDEXES.items():
        members = norgatedata.watchlist_symbols(watchlist)
        batch = []
        for sym in members:
            tid = sym_map.get(sym)
            if tid is None:
                unmapped.add(sym)
                continue
            df = norgatedata.index_constituent_timeseries(
                sym, label, timeseriesformat="pandas-dataframe")
            if df is None or df.empty:
                continue
            for frm, to in _intervals_from_timeseries(df):
                batch.append({
                    "ticker_id": tid,
                    "index_name": name,
                    "from_date": frm.date() if hasattr(frm, "date") else frm,
                    "to_date": (to.date() if (to is not None and hasattr(to, "date")) else to),
                    "source": "norgate",
                })
        if batch and not dry_run:
            ka_upsert("gws.index_membership", batch,
                      conflict_columns=["ticker_id", "index_name", "from_date"])
        n_rows += len(batch)
        print(f"{name:8} members={len(members):>5} interval_rows={len(batch):>6}"
              + ("  (dry-run)" if dry_run else ""))

    print(f"\nTotal interval rows: {n_rows}; unmapped symbols: {len(unmapped)}")
    if unmapped:
        print("UNMAPPED (review — assetid mapping hardening):",
              ", ".join(sorted(unmapped)[:20]), "..." if len(unmapped) > 20 else "")
    return {"interval_rows": n_rows, "n_unmapped": len(unmapped)}


def main() -> int:
    dry = "--dry-run" in sys.argv
    ingest(dry_run=dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
