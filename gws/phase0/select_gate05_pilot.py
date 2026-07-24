"""Gate 0.5 — pre-committed pilot-universe SELECTION (N=300), per GATE05_PILOT_PRECOMMIT.md.

STRUCTURAL CRITERIA ONLY: this script touches eligibility flags/dates, entity metadata, index
membership, split METADATA (adj_factor structure), and QC-exception flags. It never reads
prices, returns, volumes-as-signal, or move outcomes. RNG seed 20260719 is fixed in the
pre-commit; the script is fully deterministic (pools sorted by entity_id before sampling).
Output: phases/gate05_pilot_universe.csv — committed BEFORE any pilot compute runs.

Documented deviations from the pre-commit text, forced by facts found 2026-07-24 (logged in
KA_PROJECT_LOG.md; all structural, none outcome-based):
  D1  Index family 'none' added to the family stratum. The all-listed-equity deep-era rule
      (ratified 2026-07-24, after this pre-commit) makes pre-1990 first-eligibility dates
      carry no index membership; the pre-commit's three families cannot classify them.
  D2  'Delisted via bankruptcy/liquidation' has no direct field. Structural proxy: delisted
      AND (base symbol ends in 'Q' — the NASDAQ fifth-letter bankruptcy convention — OR
      company name contains a liquidation/bankruptcy marker).
  D3  'Reverse split in corporate_actions / Norgate metadata': corporate_actions holds ZERO
      split rows (dividends only). Detected instead from adj_factor structure: a forward-in-
      time drop of the cumulative factor by >=1.5x is a reverse split >= 3:2. adj_factor is
      split metadata (explicitly allowed), not price.

    python -m gws.phase0.select_gate05_pilot
"""
from __future__ import annotations

import csv
import datetime as dt
import pathlib
import re
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib

SEED = 20260719
N_STRAT = 250
N_ADV = 50
ADV_MINIMUMS = [("bankruptcy", 10), ("reverse_split", 10), ("symbol_reuse", 10),
                ("pre1980", 10), ("qc_flagged", 5)]
OUT = pathlib.Path(__file__).resolve().parents[2] / "phases" / "gate05_pilot_universe.csv"

_BASE = re.compile(r"-\d{6}$")


def base_symbol(sym: str) -> str:
    return _BASE.sub("", sym)


def era_of(d: dt.date) -> str:
    if d < dt.date(1990, 1, 1):
        return "pre1990"
    if d < dt.date(2010, 1, 1):
        return "1990_2009"
    return "2010_present"


def family_of(index_names: list[str]) -> str:
    s = set(index_names)
    if "sp500" in s:
        return "sp500"
    if s & {"sp400", "sp600"}:
        return "sp400_600"
    if s & {"r1000", "r2000", "r3000", "ndx100"}:   # ndx100 folded into the broad-index bucket
        return "russell_only"
    return "none"                                    # D1: deep-era all-listed first eligibility


def proportional_allocation(cell_sizes: dict, total: int) -> dict:
    """Floor-proportional; remainder goes to the single largest stratum (pre-commit wording)."""
    n = sum(cell_sizes.values())
    alloc = {k: min(v, (total * v) // n) for k, v in cell_sizes.items()}
    largest = max(cell_sizes, key=lambda k: (cell_sizes[k], k))
    alloc[largest] += total - sum(alloc.values())
    if alloc[largest] > cell_sizes[largest]:
        raise SystemExit(f"largest stratum {largest} cannot absorb the remainder — revisit")
    return alloc


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    rng = np.random.default_rng(SEED)

    print("loading first-eligibility + families ...", flush=True)
    fe = {r["eid"]: (r["fd"], r["fams"]) for r in conn.execute("""
        WITH fe AS (SELECT ticker_id AS eid, min(date) AS fd
                    FROM gws.universe_eligibility WHERE eligible GROUP BY 1)
        SELECT fe.eid, fe.fd,
               coalesce(array_agg(m.index_name) FILTER (WHERE m.index_name IS NOT NULL), '{}') AS fams
        FROM fe LEFT JOIN gws.index_membership m
          ON m.entity_id = fe.eid AND m.from_date <= fe.fd
         AND (m.to_date IS NULL OR m.to_date >= fe.fd)
        GROUP BY 1, 2""")}
    meta = {r["entity_id"]: r for r in conn.execute(
        "SELECT entity_id, norgate_symbol, name, is_delisted, first_quoted_date "
        "FROM ka_history.entities WHERE subtype1='Equity'")}
    ever = sorted(set(fe) & set(meta))
    print(f"  ever-eligible equities: {len(ever)}", flush=True)

    # ---- adversarial pools (structural classes) --------------------------------------
    print("building adversarial pools ...", flush=True)
    liq = re.compile(r"liquidat|bankrupt", re.IGNORECASE)
    bankruptcy = [e for e in ever if meta[e]["is_delisted"] and
                  (base_symbol(meta[e]["norgate_symbol"]).endswith("Q")
                   or liq.search(meta[e]["name"] or ""))]                       # D2

    rev = {r["entity_id"] for r in conn.execute("""
        SELECT DISTINCT entity_id FROM (
          SELECT entity_id, adj_factor,
                 lag(adj_factor) OVER (PARTITION BY entity_id ORDER BY date) AS prev
          FROM ka_history.eod_history WHERE adj_factor IS NOT NULL) s
        WHERE prev IS NOT NULL AND adj_factor > 0 AND prev / adj_factor >= 1.5""")}  # D3
    reverse_split = [e for e in ever if e in rev]

    bases: dict[str, list] = {}
    for e, m in meta.items():
        bases.setdefault(base_symbol(m["norgate_symbol"]), []).append(e)
    reuse_groups = {b: es for b, es in bases.items() if len(es) > 1}
    symbol_reuse = sorted(e for es in reuse_groups.values() for e in es if e in fe)

    pre1980 = [e for e in ever if meta[e]["first_quoted_date"]
               and meta[e]["first_quoted_date"] < dt.date(1980, 1, 1)]

    qc_entity = {r["ticker_id"] for r in conn.execute(
        "SELECT DISTINCT ticker_id FROM gws.data_quality_exceptions "
        "WHERE source IN ('assert_adjustment_fresh')")}
    qc_fmp = {r["entity_id"] for r in conn.execute(
        "SELECT DISTINCT etm.entity_id FROM gws.data_quality_exceptions d "
        "JOIN gws.entity_ticker_map etm ON etm.ticker_id = d.ticker_id "
        "WHERE d.source IN ('fmp', 'completeness_audit')")}
    qc_flagged = sorted((qc_entity | qc_fmp) & set(meta))   # excluded 17 allowed: zero-move stress

    pools = {"bankruptcy": sorted(bankruptcy), "reverse_split": sorted(reverse_split),
             "symbol_reuse": symbol_reuse, "pre1980": sorted(pre1980),
             "qc_flagged": qc_flagged}
    for k, p in pools.items():
        print(f"  pool {k:14} {len(p)}", flush=True)

    adversarial: dict[int, list] = {}
    for cls, need in ADV_MINIMUMS:
        pool = [e for e in pools[cls] if e not in adversarial]
        if len(pool) < need:
            raise SystemExit(f"adversarial pool '{cls}' has {len(pool)} < required {need} — "
                             f"escalate to Scott, do not weaken the class")
        for e in rng.choice(pool, size=need, replace=False):
            adversarial[int(e)] = [cls]
    fill_order = [cls for cls, _ in ADV_MINIMUMS]
    i = 0
    while len(adversarial) < N_ADV:
        cls = fill_order[i % len(fill_order)]
        pool = [e for e in pools[cls] if e not in adversarial]
        if pool:
            e = int(rng.choice(pool))
            adversarial[e] = [cls]
        i += 1
        if i > 1000:
            raise SystemExit("cannot fill 50 adversarial — pools exhausted")
    for e in adversarial:                                    # tag every class each pick satisfies
        adversarial[e] = sorted({c for c, p in pools.items() if e in set(p)} |
                                set(adversarial[e]))

    # ---- stratified 250 ---------------------------------------------------------------
    strat_pool = [e for e in ever if e not in adversarial]
    cell_of = {}
    for e in strat_pool:
        fd, fams = fe[e]
        cell_of[e] = (era_of(fd), "delisted" if meta[e]["is_delisted"] else "active",
                      family_of(fams))
    cells: dict[tuple, list] = {}
    for e, c in cell_of.items():
        cells.setdefault(c, []).append(e)
    alloc = proportional_allocation({c: len(es) for c, es in cells.items()}, N_STRAT)
    stratified = {}
    for c in sorted(cells):
        take = alloc.get(c, 0)
        if take:
            for e in rng.choice(sorted(cells[c]), size=take, replace=False):
                stratified[int(e)] = c

    # ---- emit ---------------------------------------------------------------------------
    rows = []
    for e, c in stratified.items():
        rows.append({"entity_id": e, "norgate_symbol": meta[e]["norgate_symbol"],
                     "kind": "stratified", "label": f"{c[0]}|{c[1]}|{c[2]}",
                     "first_eligible": fe[e][0],
                     "first_quoted": meta[e]["first_quoted_date"],
                     "is_delisted": meta[e]["is_delisted"]})
    for e, classes in adversarial.items():
        rows.append({"entity_id": e, "norgate_symbol": meta[e]["norgate_symbol"],
                     "kind": "adversarial", "label": ";".join(classes),
                     "first_eligible": fe[e][0] if e in fe else None,
                     "first_quoted": meta[e]["first_quoted_date"],
                     "is_delisted": meta[e]["is_delisted"]})
    rows.sort(key=lambda r: (r["kind"], r["entity_id"]))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"\nselected {len(stratified)} stratified + {len(adversarial)} adversarial "
          f"-> {OUT.name}")
    print("\nstratified cells (era | status | family -> n):")
    for c in sorted(alloc):
        if alloc[c]:
            print(f"  {c[0]:12} {c[1]:8} {c[2]:12} {alloc[c]:>3}  (pool {len(cells[c])})")
    counts: dict[str, int] = {}
    for classes in adversarial.values():
        for c in classes:
            counts[c] = counts.get(c, 0) + 1
    print("adversarial class coverage (with multi-tag):", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
