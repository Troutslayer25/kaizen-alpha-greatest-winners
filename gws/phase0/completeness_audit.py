"""FMP <-> Norgate cross-validation over the overlap, in RETURN space (review, lineage aspect).

The master doc asserts the two price sources are "cross-validated over the overlap"; this makes
that real. Three deliberate choices fix the disqualifying properties of the old ad-hoc crosscheck:

  1. RETURN space, not price levels. The study's stored Norgate series is CAPITALSPECIAL-adjusted
     (splits + specials, no dividend reinvestment); FMP adjusted differs by convention. Comparing
     adjusted LEVELS drifts with dividend yield over the lookback (a flat price tolerance is then
     both too tight for old bars and unrelated to the series actually read). Daily LOG RETURNS
     cancel the constant adjustment basis, so a discrepancy means a genuine data disagreement
     (a bad split factor shows up as a one-day return spike at the splice).
  2. Delisted INCLUDED. The survivorship-critical names are exactly where FMP quality is weakest;
     they must be cross-validated, not filtered out.
  3. Writes CONTIGUOUS discrepancy spans to gws.data_quality_exceptions (machine-consumed by the
     universe builder), not a human-only markdown report.

Reconciliation policy (pre-committed): on disagreement, PREFER Norgate for deep history (the
survivorship-free spine) and flag the FMP span excluded. RUNS ON ka-runner / workstation.

    python -m gws.phase0.completeness_audit                 # audit all overlapping equities
    python -m gws.phase0.completeness_audit --tol 0.02
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from gws.phase0.spans import contiguous_spans

RETURN_TOL = 0.02       # |log-return difference| above this on a traded day = disagreement
MIN_SPAN_BARS = 1


def daily_log_returns(closes):
    c = np.asarray(closes, float)
    out = np.full(len(c), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.log(c[1:] / c[:-1])
    out[1:] = np.where(np.isfinite(r), r, np.nan)
    return out


def compare_return_series(dates, close_a, close_b, *, tol: float = RETURN_TOL):
    """Align two adjusted-close series by date, compare daily log returns, and return the list
    of contiguous (from_date, to_date) spans where |return_a - return_b| > tol. NaN returns
    (warm-up / gaps on either side) are not flagged."""
    ra = daily_log_returns(close_a)
    rb = daily_log_returns(close_b)
    diff = np.abs(ra - rb)
    flags = np.isfinite(diff) & (diff > tol)
    return contiguous_spans(list(dates), list(flags))


def audit_entity(conn, entity_id, ticker_id, *, tol=RETURN_TOL):
    """Compare the stored Norgate (ka_history) and FMP (public.eod_prices) adjusted series over
    their date overlap for one name. Returns discrepancy spans (calendar dates)."""
    nor = conn.execute(
        "SELECT date, adjusted_close FROM ka_history.eod_history WHERE entity_id=%s "
        "AND adjusted_close IS NOT NULL ORDER BY date", (entity_id,)).fetchall()
    fmp = conn.execute(
        "SELECT date, adjusted_close FROM public.eod_prices WHERE ticker_id=%s "
        "AND adjusted_close IS NOT NULL ORDER BY date", (ticker_id,)).fetchall()
    nmap = {r["date"]: float(r["adjusted_close"]) for r in nor}
    fmap = {r["date"]: float(r["adjusted_close"]) for r in fmp}
    dates = sorted(set(nmap) & set(fmap))
    if len(dates) < 3:
        return []
    return compare_return_series(dates, [nmap[d] for d in dates], [fmap[d] for d in dates], tol=tol)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol", type=float, default=RETURN_TOL)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # lazy DB imports (module must import without a connection, for unit testing the core)
    import psycopg
    from psycopg.rows import dict_row
    sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    pairs = conn.execute(
        "SELECT entity_id, ticker_id FROM gws.entity_ticker_map").fetchall()
    total_spans = 0
    for r in pairs:
        spans = audit_entity(conn, r["entity_id"], r["ticker_id"], tol=args.tol)
        for frm, to in spans:
            total_spans += 1
            if not args.dry_run:
                conn.execute(
                    "INSERT INTO gws.data_quality_exceptions "
                    "(ticker_id, date_from, date_to, issue, resolution, source) "
                    "VALUES (%s,%s,%s,'fmp_norgate_return_disagreement','excluded','completeness_audit')",
                    (r["ticker_id"], frm, to))
    print(f"{len(pairs)} overlapping names; {total_spans} discrepancy spans "
          f"(tol={args.tol}){'  (dry-run)' if args.dry_run else ' written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
