"""Phase 0 gate — assert split/spinoff adjustment is COMPLETE and FRESH before any
move-detection run. RUNS ON ka-runner (reads ka_history on the local DB).

Why (review 2026-07-03 CF-2). The move detector reads ka_history.adjusted_close. If any
in-scope bar is unadjusted (adj_factor IS NULL) or the raw series was re-pulled after the
last adjustment (a split restates the whole CAPITALSPECIAL series), the adjusted series
carries a phantom cliff and the detector manufactures a fake trough + fake monster move —
Risk #4, thrown-error-free. This gate turns that silent corruption into a hard stop.

Two per-entity assertions over the study window (Equity subtype only):
  1. COVERAGE — no bar with close IS NOT NULL AND adj_factor IS NULL.
  2. FRESHNESS — max(adjusted_at) IS NOT NULL AND max(adjusted_at) >= max(ingested_at)
     (the adjustment is at least as new as the newest raw bar).

Exit non-zero if any entity fails. With --exclude, offenders are written to
gws.data_quality_exceptions (resolution='excluded') so the universe builder drops them
instead of the whole run aborting — use that once the residual set is understood (e.g. the
16 known-unfetchable Norgate names), not to paper over a fresh staleness event.

    python -m gws.phase0.assert_adjustment_fresh                       # gate, whole history
    python -m gws.phase0.assert_adjustment_fresh --study-start 1950-01-01
    python -m gws.phase0.assert_adjustment_fresh --exclude             # tag offenders, then pass
"""
from __future__ import annotations

import argparse
import sys

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib
from ka_lib import config as cfg  # noqa: E402

SCHEMA = "ka_history"


def connect():
    return psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True,
                           options=f"-c search_path={SCHEMA},public")


def find_offenders(conn, study_start=None):
    """Per-entity coverage + freshness check. Returns a list of dict rows, one per
    failing entity, each with entity_id, uncovered, raw_at, adj_at, reason."""
    where = "e.subtype1='Equity'"
    params: list = []
    if study_start:
        where += " AND h.date >= %s"
        params.append(study_start)
    q = f"""
        SELECT h.entity_id,
               count(*) FILTER (WHERE h.close IS NOT NULL AND h.adj_factor IS NULL) AS uncovered,
               max(h.ingested_at) AS raw_at,
               max(h.adjusted_at) AS adj_at
        FROM eod_history h
        JOIN entities e ON e.entity_id = h.entity_id
        WHERE {where}
        GROUP BY h.entity_id
        HAVING count(*) FILTER (WHERE h.close IS NOT NULL AND h.adj_factor IS NULL) > 0
            OR max(h.adjusted_at) IS NULL
            OR max(h.adjusted_at) < max(h.ingested_at)
    """
    offenders = []
    for r in conn.execute(q, params).fetchall():
        if r["uncovered"] and r["uncovered"] > 0:
            reason = "uncovered_bars"
        elif r["adj_at"] is None:
            reason = "never_adjusted"
        else:
            reason = "stale_adjustment"   # raw re-pulled after last adjustment
        offenders.append({**r, "reason": reason})
    return offenders


def _exclude(conn, offenders):
    rows = [(o["entity_id"], f"adjustment_{o['reason']}") for o in offenders]
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO gws.data_quality_exceptions (ticker_id, issue, resolution, source) "
            "VALUES (%s, %s, 'excluded', 'assert_adjustment_fresh')", rows)
    # ticker_id column carries the entity_id here (deep-history entity identity); the
    # universe builder resolves domain. Documented in the review remediation.


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study-start", default=None)
    ap.add_argument("--exclude", action="store_true",
                    help="tag offenders excluded in gws.data_quality_exceptions and pass")
    args = ap.parse_args()

    conn = connect()
    offenders = find_offenders(conn, args.study_start)
    if not offenders:
        print("PASS: adjustment complete and fresh for all in-scope equities.")
        return 0

    by_reason: dict[str, int] = {}
    for o in offenders:
        by_reason[o["reason"]] = by_reason.get(o["reason"], 0) + 1
    print(f"{len(offenders)} entities FAIL adjustment gate: "
          + ", ".join(f"{k}={v}" for k, v in sorted(by_reason.items())))
    for o in offenders[:20]:
        print(f"  entity {o['entity_id']}: {o['reason']} "
              f"(uncovered={o['uncovered']}, raw_at={o['raw_at']}, adj_at={o['adj_at']})")
    if len(offenders) > 20:
        print(f"  ... and {len(offenders) - 20} more")

    if args.exclude:
        _exclude(conn, offenders)
        print(f"Tagged {len(offenders)} entities excluded in gws.data_quality_exceptions. "
              f"Re-run backfill_norgate_adjusted to actually repair, don't leave excluded.")
        return 0

    print("\nHALT: run `python -m gws.phase0.backfill_norgate_adjusted --run` to refresh, "
          "or re-run this gate with --exclude once the residual set is understood.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
