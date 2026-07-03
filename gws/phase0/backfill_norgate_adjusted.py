"""Backfill split/spinoff-adjusted prices into ka_history.eod_history.

WHY: the deep-history backfill pulled Norgate with StockPriceAdjustmentType.NONE
(raw), and corporate_actions captured dividends only — zero split records. So the
stored close is split-UNADJUSTED (verified: AAPL closes 499.23 -> 129.04 across its
2020 4:1 split). Running the move detector on this manufactures a phantom crash at
every split/spinoff. This is the study's Risk #4 and it throws no error.

WHAT: additive and reversible — adds two nullable columns and fills them; the raw
`close` is never overwritten.
  adjusted_close : Norgate CAPITALSPECIAL-adjusted close (splits + special
                   distributions / spinoffs; NOT regular dividends — this is a
                   price-advance study, total-return would inflate "moves" with yield).
  adj_factor     : adjusted_close / raw close. Reconstruct adjusted OHLC as
                   raw_open*adj_factor, raw_high*adj_factor, raw_low*adj_factor.

WHERE: must run ON ka-runner — needs the NDU service (norgatedata status must be True).
It cannot run from ka-laptop (NDU not present there).

    python -m gws.phase0.backfill_norgate_adjusted --init        # add columns only
    python -m gws.phase0.backfill_norgate_adjusted --run         # fill all equities (resumable)
    python -m gws.phase0.backfill_norgate_adjusted --run --limit 50
    python -m gws.phase0.backfill_norgate_adjusted --verify      # spot-check AAPL splits
"""
from __future__ import annotations

import argparse
import math
import sys

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib
import norgatedata as nd  # noqa: E402
from ka_lib import config as cfg  # noqa: E402

SCHEMA = "ka_history"
ADJ = nd.StockPriceAdjustmentType.CAPITALSPECIAL  # splits + spinoffs/special distributions
NOPAD = nd.PaddingType.NONE


def connect():
    return psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True,
                           options=f"-c search_path={SCHEMA},public")


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(f) or math.isinf(f)) else f


def _has_col(conn, col):
    return bool(conn.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema='ka_history' "
        "AND table_name='eod_history' AND column_name=%s", (col,)).fetchone())


def cmd_init(conn):
    # Only ALTER if a column is actually missing — ADD COLUMN IF NOT EXISTS still
    # takes an ACCESS EXCLUSIVE lock even as a no-op, which can queue for a long
    # time behind unrelated long reads on this 99.5M-row hypertable.
    for col in ("adjusted_close", "adj_factor"):
        if not _has_col(conn, col):
            conn.execute(f"ALTER TABLE eod_history ADD COLUMN {col} NUMERIC")
    # adjusted_at = the vintage of the adjustment (review 2026-07-03 CF-2). The raw
    # loader sets adjusted_close/adj_factor/adjusted_at back to NULL on any raw re-pull,
    # so a stale adjustment surfaces as a countable NULL instead of a silent phantom
    # cliff. assert_adjustment_fresh.py gates on it before any detector run.
    if not _has_col(conn, "adjusted_at"):
        conn.execute("ALTER TABLE eod_history ADD COLUMN adjusted_at TIMESTAMPTZ")
    print("columns adjusted_close, adj_factor, adjusted_at present on ka_history.eod_history")


def _equities(conn, limit):
    # cheap: entities metadata only — no scan of the 99.5M-row price table.
    # resume is handled per-entity by _is_done (fast PK lookup) in cmd_run.
    q = "SELECT entity_id, norgate_symbol FROM entities WHERE subtype1='Equity' ORDER BY entity_id"
    if limit:
        q += f" LIMIT {int(limit)}"
    return conn.execute(q).fetchall()


def _is_done(conn, entity_id):
    # fast: PK (entity_id, date) index scan, newest bar only
    r = conn.execute("SELECT adj_factor FROM eod_history WHERE entity_id=%s "
                     "ORDER BY date DESC LIMIT 1", (entity_id,)).fetchone()
    return r is not None and r["adj_factor"] is not None


def backfill_one(conn, entity_id, norgate_symbol):
    df = nd.price_timeseries(norgate_symbol, stock_price_adjustment_setting=ADJ,
                             padding_setting=NOPAD, timeseriesformat="pandas-dataframe")
    if df is None or len(df) == 0:
        return 0
    rows = [(entity_id, (ts.date() if hasattr(ts, "date") else ts), _num(r.get("Close")))
            for ts, r in df.iterrows()]
    with conn.cursor() as cur:
        # session-scoped temp table; do NOT use ON COMMIT DELETE ROWS — the
        # connection is autocommit, so each INSERT would wipe the stage before
        # the UPDATE can join it. TRUNCATE per entity gives the same isolation.
        cur.execute("CREATE TEMP TABLE IF NOT EXISTS _adj_stage "
                    "(entity_id BIGINT, date DATE, adj_close NUMERIC)")
        cur.execute("TRUNCATE _adj_stage")
        cur.executemany("INSERT INTO _adj_stage VALUES (%s,%s,%s)", rows)
        # adj_factor uses raw close already in eod_history; guard divide-by-zero
        cur.execute("""
            UPDATE eod_history h
            SET adjusted_close = s.adj_close,
                adj_factor = CASE WHEN h.close > 0 THEN s.adj_close / h.close ELSE NULL END,
                adjusted_at = now()
            FROM _adj_stage s
            WHERE h.entity_id = s.entity_id AND h.date = s.date""")
        n = cur.rowcount
    return n


def cmd_run(conn, limit):
    if not nd.status():
        sys.exit("NDU not running — this command must run on ka-runner with the "
                 "Norgate Data Updater started.")
    todo = _equities(conn, limit)
    print(f"{len(todo)} equities in scope", flush=True)
    done = skipped = 0
    for i, r in enumerate(todo, 1):
        try:
            if _is_done(conn, r["entity_id"]):
                skipped += 1
            else:
                n = backfill_one(conn, r["entity_id"], r["norgate_symbol"])
                if n == 0:
                    # unfetchable (Norgate 'not found' — the ~16 remap follow-ups). Record it
                    # instead of silently counting it done (review DL M-6), so a NULL-adjusted
                    # name leaves a queryable trace and the universe builder can exclude it.
                    conn.execute(
                        "INSERT INTO gws.data_quality_exceptions "
                        "(ticker_id, issue, resolution, source) VALUES (%s, 'norgate_unfetchable', "
                        "'excluded', 'backfill_norgate_adjusted') ON CONFLICT DO NOTHING",
                        (r["entity_id"],))
                done += 1
        except Exception as e:
            print(f"  ERROR {r['norgate_symbol']}: {str(e)[:120]}", flush=True)
        if i % 200 == 0:
            print(f"  {i}/{len(todo)}  adjusted={done} skipped={skipped}  last {r['norgate_symbol']}", flush=True)
    print(f"DONE: adjusted {done}, skipped {skipped} (already done), of {len(todo)} equities", flush=True)


def cmd_verify(conn):
    row = conn.execute("SELECT entity_id FROM entities WHERE display_symbol='AAPL' "
                       "AND subtype1='Equity' LIMIT 1").fetchone()
    if not row:
        print("AAPL not found"); return
    eid = row["entity_id"]
    print("AAPL adjusted_close around 2020-08-31 (4:1) and 2014-06-09 (7:1):")
    for win in (("2020-08-27", "2020-09-02"), ("2014-06-05", "2014-06-11")):
        for r in conn.execute(
            "SELECT date, close, adjusted_close, adj_factor FROM eod_history "
            "WHERE entity_id=%s AND date BETWEEN %s AND %s ORDER BY date", (eid, *win)).fetchall():
            ac = r["adjusted_close"]
            print(f"   {r['date']}  raw {float(r['close']):>9.2f}  adj "
                  f"{float(ac) if ac is not None else float('nan'):>9.2f}")
        print("   ---")
    print("PASS if adjusted_close is continuous across each split (no ~4x / ~7x cliff).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    conn = connect()
    if args.init:
        cmd_init(conn)
    if args.run:
        cmd_init(conn)  # safe / idempotent
        cmd_run(conn, args.limit)
    if args.verify:
        cmd_verify(conn)
    if not (args.init or args.run or args.verify):
        ap.print_help()


if __name__ == "__main__":
    main()
