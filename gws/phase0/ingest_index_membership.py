"""Phase 0, Step 1 — ingest historical PIT index-constituent membership.

RUNS ON ka-runner (Norgate NDU + Postgres). Cannot be executed on ka-laptop.
Critical-path blocker #1: the production DB has NO index-membership table, and the
entire universe quality filter depends on it. This builds `gws.index_membership` as
PIT from/to intervals from Norgate's constituent timeseries, INCLUDING delisted
members (survivorship-free).

Prerequisite: Step 0 (verify_norgate_index_coverage.py) confirmed the index labels and
coverage. Do not run this until Step 0 is GO.

KEYING (review 2026-07-03 CF-1). Membership is keyed on Norgate `assetid` (=
`ka_history.entities.entity_id`), the permanent identity that also exists for delisted
and pre-2010 names. The previous draft mapped by CURRENT symbol against `public.tickers`
(~7,250 live FMP symbols): every delisted / pre-2010 constituent silently failed to map
and was dropped, and recycled symbols mis-attributed to the wrong company — reintroducing
survivorship bias into the one table meant to prevent it. This version:
  * resolves each watchlist symbol to its assetid and requires that assetid to exist in
    ka_history.entities (so its prices are joinable);
  * closes an open interval on a DELISTED entity at its last traded date (NULL to_date is
    reserved for names that are still listed AND still members);
  * persists every unresolved symbol to gws.index_membership_unmapped;
  * HALTs (exit non-zero) when the unmapped fraction exceeds --max-unmapped-frac — a
    silently short universe must fail loudly, not warn.

The FMP-era public join (tickers.id) is a SEPARATE concern handled by gws.entity_ticker_map,
not this ingester.
"""
from __future__ import annotations

import argparse
import sys


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


def _as_date(v):
    return v.date() if hasattr(v, "date") else v


def close_open_interval(to_date, *, is_delisted, last_quoted_date):
    """Resolve a NULL (open) to_date. A delisted entity stopped being a member when it
    stopped trading — close it at its last quoted date. Only a still-listed entity keeps
    an open (NULL) interval. Non-open intervals pass through unchanged."""
    if to_date is not None:
        return _as_date(to_date)
    if is_delisted:
        return _as_date(last_quoted_date)   # may be None if Norgate lacks it — then genuinely open
    return None


def build_interval_rows(members, entities, *, index_name, constituent_series, assetid_of):
    """Pure core (testable without NDU). `entities` maps assetid -> {is_delisted,
    last_quoted_date}. `assetid_of(sym)` -> assetid or None. `constituent_series(sym)` ->
    a constituent DataFrame or None. Returns (rows, unmapped) where unmapped is a list of
    (symbol, reason)."""
    rows, unmapped = [], []
    for sym in members:
        aid = assetid_of(sym)
        if aid is None:
            unmapped.append((sym, "no_assetid"))
            continue
        ent = entities.get(aid)
        if ent is None:
            unmapped.append((sym, "assetid_not_in_ka_history"))
            continue
        df = constituent_series(sym)
        if df is None or df.empty:
            continue
        for frm, to in _intervals_from_timeseries(df):
            rows.append({
                "entity_id": int(aid),
                "index_name": index_name,
                "from_date": _as_date(frm),
                "to_date": close_open_interval(
                    to, is_delisted=ent["is_delisted"], last_quoted_date=ent["last_quoted_date"]),
                "source": "norgate",
            })
    return rows, unmapped


def _load_entities() -> dict:
    from ka_lib.db import ka_query  # ka-runner only
    rows = ka_query("SELECT entity_id, is_delisted, last_quoted_date FROM ka_history.entities")
    return {int(r["entity_id"]): {"is_delisted": r["is_delisted"],
                                  "last_quoted_date": r["last_quoted_date"]} for r in rows}


def ingest(dry_run: bool = False, max_unmapped_frac: float = 0.05) -> dict:
    import norgatedata  # ka-runner only
    from ka_lib.db import ka_upsert  # ka-runner only

    from gws.phase0.verify_norgate_index_coverage import TARGET_INDEXES

    entities = _load_entities()

    def assetid_of(sym):
        try:
            return norgatedata.assetid(sym)
        except Exception:
            return None

    def constituent_series(sym, label):
        return norgatedata.index_constituent_timeseries(
            sym, label, timeseriesformat="pandas-dataframe")

    n_rows = n_members = 0
    all_unmapped = []
    for name, (label, watchlist) in TARGET_INDEXES.items():
        members = norgatedata.watchlist_symbols(watchlist)
        rows, unmapped = build_interval_rows(
            members, entities, index_name=name,
            constituent_series=lambda s: constituent_series(s, label),
            assetid_of=assetid_of)
        if rows and not dry_run:
            ka_upsert("gws.index_membership", rows,
                      conflict_columns=["entity_id", "index_name", "from_date"])
        if unmapped and not dry_run:
            ka_upsert("gws.index_membership_unmapped",
                      [{"norgate_symbol": s, "index_name": name, "reason": r} for s, r in unmapped],
                      conflict_columns=["norgate_symbol", "index_name"])
        n_rows += len(rows)
        n_members += len(members)
        all_unmapped += [(s, name, r) for s, r in unmapped]
        print(f"{name:8} members={len(members):>5} interval_rows={len(rows):>6} "
              f"unmapped={len(unmapped):>4}" + ("  (dry-run)" if dry_run else ""))

    frac = (len(all_unmapped) / n_members) if n_members else 0.0
    print(f"\nTotal interval rows: {n_rows}; unmapped symbols: {len(all_unmapped)} "
          f"({frac:.1%} of {n_members} member-slots)")
    if all_unmapped:
        preview = ", ".join(f"{s}[{r}]" for s, _, r in all_unmapped[:20])
        print("UNMAPPED (persisted to gws.index_membership_unmapped):", preview,
              "..." if len(all_unmapped) > 20 else "")

    result = {"interval_rows": n_rows, "n_unmapped": len(all_unmapped),
              "unmapped_frac": frac, "member_slots": n_members}
    if frac > max_unmapped_frac:
        print(f"\nHALT: unmapped fraction {frac:.1%} exceeds --max-unmapped-frac "
              f"{max_unmapped_frac:.1%}. A short universe silently describes the wrong "
              f"population — resolve assetid mapping before proceeding.", file=sys.stderr)
        result["halt"] = True
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-unmapped-frac", type=float, default=0.05)
    args = ap.parse_args()
    result = ingest(dry_run=args.dry_run, max_unmapped_frac=args.max_unmapped_frac)
    return 1 if result.get("halt") else 0


if __name__ == "__main__":
    sys.exit(main())
