"""Workbook recall QC (validation-only; NO outcome analysis) — run the six-family
detector over the tickers in Scott's hand-labeled BO tape (2017–2021 pre-lockbox) and
measure how often the machine fires within ±5 bars of his labeled events. Events persist
under run_id 'workbook_recall_qc' for permanence; nothing analytical reads them.

    python -m gws.phase_a1.run_workbook_recall
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

from gws.phase_a1.detect_anchor_events import P, load_series, run_variant  # noqa: E402

WB = pathlib.Path(r"C:\Users\scott\Desktop\Kaizen-Alpha Reports\studies"
                  r"\trendline_workbook_2026-07-16\ka_trendline_breakouts.csv")
RUN = "workbook_recall_qc"


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    wb = pd.read_csv(WB, parse_dates=["date"])
    wb = wb[wb["date"] < "2022-01-01"].copy()
    syms = sorted(wb["ticker"].unique())
    rows = conn.execute(
        "SELECT entity_id, norgate_symbol, is_delisted, last_quoted_date "
        "FROM ka_history.entities WHERE subtype1='Equity'").fetchall()
    active = {r["norgate_symbol"]: r["entity_id"] for r in rows if not r["is_delisted"]}
    delisted = {}
    for r in rows:
        if r["is_delisted"]:
            base = r["norgate_symbol"].rsplit("-", 1)[0]
            delisted.setdefault(base, []).append((r["last_quoted_date"], r["entity_id"]))
    sym_eid = {}
    for s in syms:
        if s in active:
            sym_eid[s] = active[s]
        elif s in delisted:                       # latest-listed delisted bearer
            sym_eid[s] = sorted(delisted[s])[-1][1]
    print(f"tape tickers: {len(syms)}, resolved: {len(sym_eid)}", flush=True)

    cache = {}
    for i, (s, eid) in enumerate(sorted(sym_eid.items()), 1):
        ser = load_series(conn, eid)
        if ser is not None:
            cache[eid] = ser
        if i % 200 == 0:
            print(f"  loaded {i}/{len(sym_eid)}", flush=True)
    counts, total = run_variant(conn, cache, RUN, P)
    print(f"detected {total} events on tape universe {counts}", flush=True)

    ev = pd.DataFrame(conn.execute(
        "SELECT ticker_id, event_date, family FROM gws.anchor_events WHERE run_id=%s",
        (RUN,)).fetchall())
    by_tk = {tk: sorted(g["event_date"]) for tk, g in ev.groupby("ticker_id")}
    wb["eid"] = wb["ticker"].map(sym_eid)
    wbm = wb.dropna(subset=["eid"])
    hits = 0
    fam_hit: dict = {}
    for r in wbm.itertuples():
        ds = by_tk.get(int(r.eid), [])
        near = [d for d in ds if abs((d - r.date.date()).days) <= 7]
        if near:
            hits += 1
            fams = set(ev[(ev["ticker_id"] == int(r.eid))
                          & (ev["event_date"].isin(near))]["family"])
            for f in fams:
                fam_hit[f] = fam_hit.get(f, 0) + 1
    print(f"\nRECALL: {hits}/{len(wbm)} = {100 * hits / len(wbm):.1f}% of Scott's labeled "
          f"events have a detector event within ±7 calendar days")
    print(f"family attribution among hits: {dict(sorted(fam_hit.items()))}")
    print(f"by label type:")
    for t, g in wbm.groupby("type"):
        h = sum(1 for r in g.itertuples()
                if any(abs((d - r.date.date()).days) <= 7
                       for d in by_tk.get(int(r.eid), [])))
        print(f"  {t:10} {h}/{len(g)} = {100 * h / len(g):.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
