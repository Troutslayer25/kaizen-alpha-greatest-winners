"""Family-F hardening gate + workbook recall validation (trendline path, 2026-07-25).

1. Detect F under strict-PIT confirmation (f_confirm=10), persist as
   banchor3_pilot:f_confirm=10, run the full analysis harness on it, compare to primary F.
2. Workbook recall: Scott's hand-labeled BO log (1,599 general breakout/gap events,
   2017-07-12..2021-12-31 usable pre-lockbox) vs the six-family catalog — % of his labeled
   (ticker, date) events with ANY family event within ±3 bars, on tickers resolvable in
   the pilot's 250 names. Detector-QC only; no outcome analysis on workbook rows.

    python -m gws.phase_a1.run_f_hardening
"""
from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

from gws.phase_a1.detect_anchor_events import P, RUN, load_series, run_variant  # noqa: E402
from gws.phase_a1.run_gate05_detection import RUN_ID as MOVES_RUN_ID  # noqa: E402
from gws.phase_a1.run_gate05_detection import bench_map, load_pilot   # noqa: E402
from gws.phase_a1.series_guard import assert_series_hash              # noqa: E402

import numpy as np                                                     # noqa: E402

from gws.phase_a1.run_b_anchor3_analysis import analyze                # noqa: E402
from gws.phase_a2.feature_matrix import build_feature_matrix           # noqa: E402

SEED = 20260719
EVID = pathlib.Path(__file__).resolve().parents[2] / "phases" / "gate05_evidence"
WB = pathlib.Path(r"C:\Users\scott\Desktop\Kaizen-Alpha Reports\studies"
                  r"\trendline_workbook_2026-07-16\ka_trendline_breakouts.csv")


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    pilot = load_pilot()
    strat = {int(r["entity_id"]): r["norgate_symbol"] for r in pilot
             if r["kind"] == "stratified"}

    cache, date_idx, bench_by_ticker = {}, {}, {}
    bench = bench_map()
    for eid in strat:
        s = load_series(conn, eid)
        if s is None:
            continue
        assert_series_hash(conn, MOVES_RUN_ID, eid, s[0])
        cache[eid] = s
        date_idx[eid] = {dd: i for i, dd in enumerate(s[0])}
        bench_by_ticker[eid] = np.array([bench.get(dd, np.nan) for dd in s[0]])

    # ---- 1. strict-PIT F ---------------------------------------------------------------
    run_id = f"{RUN}:f_confirm=10"
    counts, total = run_variant(conn, cache, run_id, {**P, "f_confirm": 10},
                                fams=frozenset("F"))
    print(f"hardened F: {total} events (primary F was 7,913)", flush=True)

    series = {eid: {"close": c, "high": h, "low": lo, "volume": v}
              for eid, (d, o, h, lo, c, v) in cache.items()}
    out = {}
    for tag, rid in (("primary", RUN), ("hardened", run_id)):
        ev = pd.DataFrame(conn.execute(
            "SELECT ticker_id, event_date, outcome FROM gws.anchor_events "
            "WHERE run_id=%s AND family='F' AND outcome IN ('winner','failed')",
            (rid,)).fetchall())
        ev["idx0"] = [date_idx.get(tk, {}).get(d)
                      for tk, d in zip(ev["ticker_id"], ev["event_date"])]
        ev = ev.dropna(subset=["idx0"]).astype({"idx0": int})
        ev["as_of_index"] = ev["idx0"] - 1
        ev = ev[ev["as_of_index"] >= 252].reset_index(drop=True)
        ev["y"] = (ev["outcome"] == "winner").astype(int)
        fm = build_feature_matrix(ev, series, bench_by_ticker=bench_by_ticker,
                                  include_generic=True, vectorized=True, n_jobs=16)
        res = analyze(ev, fm)
        res["win_rate"] = float(ev["y"].mean())
        out[tag] = res
        print(f"F[{tag}]: n={res['n']} win%={100 * res['win_rate']:.1f} "
              f"AUC={res['auc']:.3f} null_hi={max(res['shuffle'][1], res['cyclic_roll'][1]):.3f} "
              f"deleak={'OK' if res['deleak_clean'] else 'FLAG'} "
              f"clears={res['clears_null']}", flush=True)

    # ---- 2. workbook recall (detector QC only) ------------------------------------------
    wb = pd.read_csv(WB, parse_dates=["date"])
    wb = wb[wb["date"] < "2022-01-01"]
    sym_to_eid = {}
    for r in conn.execute(
            "SELECT entity_id, norgate_symbol FROM ka_history.entities "
            "WHERE NOT is_delisted AND subtype1='Equity'"):
        sym_to_eid[r["norgate_symbol"]] = r["entity_id"]
    wb["eid"] = wb["ticker"].map(sym_to_eid)
    on_pilot = wb[wb["eid"].isin(strat)].copy()
    print(f"workbook events pre-lockbox: {len(wb)}; on pilot names: {len(on_pilot)}",
          flush=True)
    rec = {"n_workbook_prelockbox": len(wb), "n_on_pilot": len(on_pilot)}
    if len(on_pilot):
        evs = pd.DataFrame(conn.execute(
            "SELECT ticker_id, event_date, family FROM gws.anchor_events WHERE run_id=%s",
            (RUN,)).fetchall())
        by_tk = {tk: g["event_date"].tolist() for tk, g in evs.groupby("ticker_id")}
        hits = fam_hits = 0
        for r in on_pilot.itertuples():
            ds = by_tk.get(int(r.eid), [])
            if any(abs((d - r.date.date()).days) <= 5 for d in ds):
                hits += 1
        rec["recall_any_family_pm5cal"] = hits / len(on_pilot)
        print(f"recall (any family, ±5 calendar days): {hits}/{len(on_pilot)} "
              f"= {100 * hits / len(on_pilot):.0f}%", flush=True)

    out["workbook_recall"] = rec
    with (EVID / "f_hardening.json").open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("evidence -> f_hardening.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
