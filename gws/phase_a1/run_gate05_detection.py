"""Gate 0.5 pilot — scope steps 1–2: MFE detection + move-catalog persistence on the
pre-committed 300-name pilot universe (phases/gate05_pilot_universe.csv, commit 292524d).

All parameters at method-library defaults: scales (2, 6, 15) x ATR-21 trailing stop,
min_duration 1. PRIMARY SCALE = 'trail_6' — the A1 pre-commit references "a pre-committed
primary scale" but never pinned the value (capability gap, LOGGED per the pilot's
no-parameter-changes rule): the middle scale is the recommended default, flagged for Scott's
ratification in the exit memo. Benchmark = Norgate $SPX (1928+), fetched via NDU at runtime
(ka_history carries no index series), aligned per-ticker by date.

Lockbox: detection window is capped at LOCKBOX_START inside detect_moves_for_ticker.
Idempotency (checklist): every run prints a catalog fingerprint (row count + SHA-256 over the
sorted natural keys); two consecutive runs must print identical fingerprints.

    python -m gws.phase_a1.run_gate05_detection
"""
from __future__ import annotations

import csv
import hashlib
import pathlib
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib

from gws.phase_a1.detect_driver import detect_moves_for_ticker      # noqa: E402
from gws.phase_a1.persist_moves import persist_moves                # noqa: E402

PILOT_CSV = pathlib.Path(__file__).resolve().parents[2] / "phases" / "gate05_pilot_universe.csv"
RUN_ID = "gate05_pilot"
SCALES = (2.0, 6.0, 15.0)
ATR_PERIOD = 21
PRIMARY_SCALE = "trail_6"      # recommended default — ratify in the Gate 0.5 exit memo
BENCH_SYMBOL = "$SPX"


def load_pilot() -> list[dict]:
    with PILOT_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bench_map() -> dict:
    import norgatedata
    df = norgatedata.price_timeseries(BENCH_SYMBOL, timeseriesformat="pandas-dataframe")
    return {ts.date(): float(c) for ts, c in df["Close"].items()}


def catalog_fingerprint(conn, run_id: str = RUN_ID) -> tuple[int, str]:
    rows = conn.execute(
        "SELECT id_domain, ticker_id, start_date, scale, detection_system, direction "
        "FROM gws.moves WHERE run_id=%s ORDER BY 1,2,3,4,5,6", (run_id,)).fetchall()
    h = hashlib.sha256()
    for r in rows:
        h.update(repr(sorted(r.items())).encode())
    return len(rows), h.hexdigest()[:16]


def main() -> int:
    import argparse
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    from gws.phase_a1.reset_derived import children_row_count

    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=RUN_ID)
    args = ap.parse_args()
    run_id = args.run_id

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    # C1 guard (Gate 0→A1 review): with FK children present, per-ticker DELETEs raise and get
    # swallowed → silently stale catalog with a PASSING fingerprint. Refuse to start instead.
    n_children = children_row_count(conn)
    if n_children:
        print(f"REFUSING TO RUN: {n_children} rows exist in gws.moves FK children "
              f"(matched_controls/setup_labels/entry_candidates). Run "
              f"`python -m gws.phase_a1.reset_derived` first — children are derived artifacts "
              f"and are rebuilt after detection.", file=sys.stderr)
        return 1
    pilot = load_pilot()
    bench = bench_map()
    print(f"pilot names: {len(pilot)}; benchmark {BENCH_SYMBOL} bars: {len(bench)}", flush=True)

    detect_params = {"scales": list(SCALES), "atr_period": ATR_PERIOD, "min_duration": 1,
                     "primary_scale": PRIMARY_SCALE, "bench": BENCH_SYMBOL,
                     "hl_adjusted": True, "lockbox_capped": True}
    n_moves = n_zero = n_err = 0
    per_kind: dict = {}
    errors = []
    hash_rows = []
    for i, row in enumerate(pilot, 1):
        eid = int(row["entity_id"])
        try:
            dates, close, high, low, volume, by_scale = detect_moves_for_ticker(
                conn, eid, source="norgate", scales=SCALES, atr_period=ATR_PERIOD)
            if dates:
                sha = hashlib.sha256("|".join(str(d) for d in dates).encode()).hexdigest()[:32]
                hash_rows.append((run_id, eid, len(dates), sha))
            moves = [m for ms in by_scale.values() for m in ms]
            if not dates or not moves:
                persist_moves(conn, eid, [], dates, close, run_id=run_id)   # clears stale rows
                n_zero += 1
                continue
            b = np.array([bench.get(d, np.nan) for d in dates])
            n = persist_moves(conn, eid, moves, dates, close, high, low, volume,
                              bench_close=b, primary_scale=PRIMARY_SCALE,
                              detect_params=detect_params, run_id=run_id)
            n_moves += n
            k = row.get("kind", "untagged")
            per_kind[k] = per_kind.get(k, 0) + n
        except Exception as e:  # noqa: BLE001 — per-ticker isolation; the run must finish
            n_err += 1
            errors.append((row["norgate_symbol"], str(e)[:120]))
        if i % 50 == 0:
            print(f"  {i}/{len(pilot)}: {n_moves} moves, {n_zero} zero-move, {n_err} errors",
                  flush=True)

    with conn.cursor() as cur:      # M3 guard: later stages assert against these hashes
        cur.execute("DELETE FROM gws.detection_series_hash WHERE run_id=%s", (run_id,))
        cur.executemany("INSERT INTO gws.detection_series_hash (run_id, ticker_id, n_bars, "
                        "dates_sha) VALUES (%s,%s,%s,%s)", hash_rows)

    print(f"\nmoves persisted: {n_moves} {per_kind}; zero-move names: {n_zero}; "
          f"errors: {n_err}")
    for sym, msg in errors:
        print(f"  ERROR {sym}: {msg}")
    cnt, fp = catalog_fingerprint(conn, run_id)
    print(f"catalog fingerprint: rows={cnt} sha={fp}")
    if n_err:
        print("ERRORS PRESENT — the catalog is NOT trustworthy for downstream stages "
              "(review C1): resolve every error and re-run before composing.",
              file=sys.stderr)
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
