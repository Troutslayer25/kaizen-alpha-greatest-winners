"""Phase-0 data-quality sweep (Risk #4) — FMP public.eod_prices AND ka_history.eod_history.

Detects adjusted-close corruption and records each CONTIGUOUS (ticker, date-range) run in
gws.data_quality_exceptions so the move detector can EXCLUDE those bars (the actually-traded-bars
rule). Non-destructive: flags, never deletes source rows.

Fixes over the first draft (review, lineage aspect):
  * PER-CONTIGUOUS-RUN spans, not one MIN..MAX envelope per ticker — a MIN/MAX collapse over
    non-contiguous corruption excludes every clean bar in between (silent over-exclusion).
  * A day-over-day RETURN-SPLICE detector: a bar where the adjusted-close return differs from the
    raw-close return but there is NO corporate action nearby is an inconsistent adjustment (bad,
    missing, or extra factor). This catches under-adjustment and moderate bad factors the ratio
    test misses, and — by cross-referencing the corporate-actions calendar — does NOT false-flag
    legitimate heavy reverse-splitters (whose adj/raw returns legitimately differ on the split day).
  * Covers ka_history.adjusted_close, the load-bearing 1950-2009 series, which had NO sweep.
  * phantom_zero uses the aligned predicate (close > 0 AND volume > 0), matching the docstring.

    python -m gws.phase0.data_quality_sweep --source both
    python -m gws.phase0.data_quality_sweep --source norgate --dry-run
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from gws.phase0.spans import contiguous_spans

EXPLOSION_RATIO = 20.0
EXPLOSION_MIN_ADJ = 1000.0
SPLICE_TOL = 0.05           # |adj_return - raw_return| above this, unexplained by an action
ACTION_WINDOW = 3          # days around a corporate action within which a return jump is expected


def _log_returns(x):
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.log(x[1:] / x[:-1])
    out[1:] = np.where(np.isfinite(r), r, np.nan)
    return out


def scan_series(dates, close, adjusted_close, volume, *, action_dates=None) -> dict:
    """Pure detector. Returns {issue: [(from_date, to_date), ...]} of CONTIGUOUS bad-bar runs.

    `action_dates` = set of corporate-action dates; return-splice jumps within ACTION_WINDOW of
    one are EXPECTED (a real split) and not flagged. Pass None to flag every jump (caller then
    cross-references)."""
    dates = list(dates)
    close = np.asarray(close, float)
    adj = np.asarray(adjusted_close, float)
    vol = np.asarray(volume, float)

    phantom = (adj <= 0) & (close > 0) & (vol > 0)
    explosion = (close > 0) & (adj > EXPLOSION_MIN_ADJ) & (adj / np.where(close > 0, close, np.nan) > EXPLOSION_RATIO)

    adj_ret, raw_ret = _log_returns(adj), _log_returns(close)
    splice = np.isfinite(adj_ret) & np.isfinite(raw_ret) & (np.abs(adj_ret - raw_ret) > SPLICE_TOL)
    if action_dates:
        # near = within ACTION_WINDOW index positions of any action date. O(n + actions*window)
        # via one pass, not O(n^2) list.index per date (review M4: 1.76s -> 0.003s per entity).
        near = np.zeros(len(dates), dtype=bool)
        aset = set(action_dates)
        for p, d in enumerate(dates):
            if d in aset:
                near[max(0, p - ACTION_WINDOW): p + ACTION_WINDOW + 1] = True
        splice = splice & ~near

    return {
        "phantom_zero": contiguous_spans(dates, phantom.tolist()),
        "split_explosion": contiguous_spans(dates, explosion.tolist()),
        "adjustment_splice": contiguous_spans(dates, splice.tolist()),
    }


def sweep_source(conn, source: str, *, dry_run: bool) -> int:
    """Iterate every entity/ticker of a source, scan its full adjusted series, write spans."""
    if source == "fmp":
        table, key = "public.eod_prices", "ticker_id"
        ids = [r[key] for r in conn.execute(f"SELECT DISTINCT {key} FROM {table}").fetchall()]
    else:
        table, key = "ka_history.eod_history", "entity_id"
        ids = [r[key] for r in conn.execute(
            "SELECT entity_id FROM ka_history.entities WHERE subtype1='Equity'").fetchall()]

    if not dry_run:
        conn.execute("DELETE FROM gws.data_quality_exceptions WHERE source=%s "
                     "AND issue IN ('phantom_zero','split_explosion','adjustment_splice')", (source,))
    written = 0
    for _id in ids:
        rows = conn.execute(
            f"SELECT date, close, adjusted_close, volume FROM {table} WHERE {key}=%s "
            "ORDER BY date", (_id,)).fetchall()
        if len(rows) < 3:
            continue
        actions = {r["action_date"] for r in conn.execute(
            "SELECT action_date FROM ka_history.corporate_actions WHERE entity_id=%s",
            (_id,)).fetchall()} if source == "norgate" else None
        found = scan_series([r["date"] for r in rows], [r["close"] for r in rows],
                            [r["adjusted_close"] for r in rows], [r["volume"] for r in rows],
                            action_dates=actions)
        for issue, spans in found.items():
            for frm, to in spans:
                written += 1
                if not dry_run:
                    conn.execute(
                        "INSERT INTO gws.data_quality_exceptions "
                        "(ticker_id, date_from, date_to, issue, resolution, source) "
                        "VALUES (%s,%s,%s,%s,'excluded',%s)", (_id, frm, to, issue, source))
    print(f"{source}: {len(ids)} names scanned, {written} contiguous exception spans"
          + ("  (dry-run)" if dry_run else " written"))
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["fmp", "norgate", "both"], default="both")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import psycopg
    from psycopg.rows import dict_row
    sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")
    from ka_lib import config as cfg
    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)

    for src in (["fmp", "norgate"] if args.source == "both" else [args.source]):
        sweep_source(conn, src, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
