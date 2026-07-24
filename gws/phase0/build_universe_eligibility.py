"""Phase 0 — full rebuild of gws.universe_eligibility (all equities, all history).

Driver around the TESTED pure core (universe.build_eligibility) — semantics live there,
including the deep-era all-listed-equity rule (INDEX_GATE_START) and the lockbox (rows on/after
LOCKBOX_START are persisted but never eligible). This driver only fetches, fans out, and COPYs.

- ID domain: `ticker_id` column carries Norgate entity_id (single-domain rule, review C1).
- Price floor / data_valid use RAW close (actual traded price) — adjusted_close would deflate
  deep history below any floor (1980s AAPL ≈ cents adjusted) and silently erase the deep eras.
- Whole-entity exclusions (assert_adjustment_fresh --exclude) produce all-dates-ineligible rows.
- Full rebuild = TRUNCATE + COPY (single writer of this table; re-run == same result).
- index_list stays NULL: index family at a date is derived from gws.index_membership directly.

    python -m gws.phase0.build_universe_eligibility [--workers 16] [--limit N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib

CHUNK = 100
_CONN = None


def _conn():
    global _CONN
    if _CONN is None:
        import psycopg
        from psycopg.rows import dict_row
        from ka_lib import config as cfg
        _CONN = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    return _CONN


def _f(v):
    return float(v) if v is not None else float("nan")


def process_chunk(work) -> tuple[int, int]:
    """work = list of (entity_id, entity_excluded). Returns (rows_written, eligible_rows)."""
    import numpy as np
    from gws.phase0.universe import build_eligibility

    conn = _conn()
    ids = [eid for eid, _ in work]
    intervals: dict[int, list] = {}
    for r in conn.execute(
            "SELECT entity_id, from_date, to_date FROM gws.index_membership "
            "WHERE entity_id = ANY(%s)", (ids,)):
        intervals.setdefault(r["entity_id"], []).append((r["from_date"], r["to_date"]))

    n_rows = n_elig = 0
    for eid, excluded in work:
        # fetch FULLY before opening the COPY — a query on a connection with an active
        # COPY deadlocks (found on first smoke run 2026-07-24)
        bars = conn.execute(
            "SELECT date, close, volume FROM ka_history.eod_history "
            "WHERE entity_id=%s ORDER BY date", (eid,)).fetchall()
        if not bars:
            continue
        dates = [b["date"] for b in bars]
        close = np.array([_f(b["close"]) for b in bars])
        volume = np.array([_f(b["volume"]) for b in bars])
        rows = build_eligibility(dates, close, volume, intervals.get(eid, []),
                                 entity_excluded=excluded)
        with conn.cursor() as cur:
            with cur.copy(
                    "COPY gws.universe_eligibility "
                    "(ticker_id, date, eligible, index_member, data_valid, above_min_price, "
                    "adv_50d, dollar_volume_50d) FROM STDIN") as copy:
                for r in rows:
                    copy.write_row((
                        eid, r["date"], r["eligible"], r["index_member"], r["data_valid"],
                        r["above_min_price"],
                        None if r["adv_50d"] != r["adv_50d"] else r["adv_50d"],
                        None if r["dollar_volume_50d"] != r["dollar_volume_50d"]
                        else r["dollar_volume_50d"]))
                    n_rows += 1
                    n_elig += r["eligible"]
    return n_rows, n_elig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=None, help="entity cap for a smoke run")
    args = ap.parse_args()

    from gws.phase0.exclusions import excluded_ids

    conn = _conn()
    excluded = excluded_ids(conn, sources=("assert_adjustment_fresh",))
    q = "SELECT entity_id FROM ka_history.entities WHERE subtype1='Equity' ORDER BY entity_id"
    if args.limit:
        q += f" LIMIT {int(args.limit)}"
    ents = [r["entity_id"] for r in conn.execute(q)]
    work = [(eid, eid in excluded) for eid in ents]
    chunks = [work[i:i + CHUNK] for i in range(0, len(work), CHUNK)]

    conn.execute("TRUNCATE gws.universe_eligibility")
    print(f"{len(ents)} equities ({len(excluded)} whole-entity excluded), "
          f"{len(chunks)} chunks x {CHUNK}, {args.workers} workers; table truncated", flush=True)

    total = elig = done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for n, e in ex.map(process_chunk, chunks):
            total += n
            elig += e
            done += 1
            if done % 10 == 0 or done == len(chunks):
                print(f"  {done}/{len(chunks)} chunks; {total:,} rows ({elig:,} eligible)",
                      flush=True)

    print(f"\nDONE {dt.datetime.now():%H:%M:%S}: {total:,} rows, {elig:,} eligible")
    return 0


if __name__ == "__main__":
    sys.exit(main())
