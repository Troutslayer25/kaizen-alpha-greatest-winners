"""Post-persist catalog audits for gws.moves (review, recommended step_09-style checks).

Standing sanity checks that catch the silent-corruption classes the reviews flagged — phantom
mega-moves, never-closing ATR-poisoned moves, row-internal inconsistency, cross-domain span
collisions, and JSONB null-coverage drift. The predicate cores are pure (row dicts in, offending
rows out) and unit-tested; `run_audits(conn)` executes them against the live catalog (lazy DB)."""
from __future__ import annotations

import json


def phantom_move_rows(rows, max_gain: float = 100.0):
    """Canary for C-3: a move with total_pct_gain > max_gain (a +10,000% is almost surely a
    phantom-zero artifact) or a NULL gain."""
    return [r for r in rows if r.get("total_pct_gain") is None or r["total_pct_gain"] > max_gain]


def open_move_violations(rows):
    """C-2: at most ONE open move per (ticker_id, scale, detection_system). More than one means a
    NaN-poisoned ATR never let the trailing stop fire."""
    counts: dict = {}
    for r in rows:
        if r.get("is_open"):
            k = (r["ticker_id"], r.get("scale"), r.get("detection_system"))
            counts[k] = counts.get(k, 0) + 1
    return {k: c for k, c in counts.items() if c > 1}


def magnitude_consistency_violations(rows, tol: float = 1e-6):
    """M-4: the typed total_pct_gain (detector, clean data) must match descriptors->>'magnitude'
    (characterization). Divergence means characterization ran on different bars than detection."""
    bad = []
    for r in rows:
        desc = r.get("descriptors")
        desc = json.loads(desc) if isinstance(desc, str) else (desc or {})
        m = desc.get("magnitude")
        g = r.get("total_pct_gain")
        # psycopg3 returns NUMERIC as decimal.Decimal; the JSONB magnitude is a float. float(...)
        # both so a Decimal-minus-float TypeError can't crash the audit on real rows (review M1).
        if m is not None and g is not None and abs(float(m) - float(g)) > tol:
            bad.append(r)
    return bad


def cross_domain_span_ids(exception_rows):
    """C-1: ticker_id values that appear under BOTH an FMP-domain and a Norgate-domain source in
    data_quality_exceptions — these must be reconciled before any mixed-source detection."""
    fmp = {r["ticker_id"] for r in exception_rows if r["source"] in ("fmp", "completeness_audit")}
    nor = {r["ticker_id"] for r in exception_rows
           if r["source"] in ("norgate", "backfill_norgate_adjusted", "assert_adjustment_fresh")}
    return fmp & nor


def null_coverage(rows, bag: str, fields):
    """M-2/M-3 visibility: fraction of rows with each JSONB field non-null, so silent erasure /
    hidden availability gates are observable."""
    n = len(rows) or 1
    out = {}
    for f in fields:
        present = 0
        for r in rows:
            d = r.get(bag)
            d = json.loads(d) if isinstance(d, str) else (d or {})
            present += d.get(f) is not None
        out[f] = present / n
    return out


def run_audits(conn) -> dict:
    """Execute all audits against the live catalog. Returns a summary dict; non-empty phantom /
    open-move / consistency results are failures to investigate before trusting the catalog."""
    rows = conn.execute(
        "SELECT ticker_id, scale, detection_system, is_open, total_pct_gain, descriptors "
        "FROM gws.moves").fetchall()
    exc = conn.execute("SELECT ticker_id, source FROM gws.data_quality_exceptions").fetchall()
    return {
        "phantom_moves": len(phantom_move_rows(rows)),
        "open_move_violations": len(open_move_violations(rows)),
        "magnitude_inconsistencies": len(magnitude_consistency_violations(rows)),
        "cross_domain_span_ids": len(cross_domain_span_ids(exc)),
        "n_moves": len(rows),
    }
