"""B-anchor-3 analysis gate (spec 36a13da §3–§6): winners vs FAILED per family, features
at B−1 + frozen context block, full harness, decision matrix on Family A.

    python -m gws.phase_a1.run_b_anchor3_analysis
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

from gws.common.negative_controls import shift_labels_within_ticker, shuffle_labels  # noqa: E402
from gws.phase_a1.detect_anchor_events import RUN, load_series        # noqa: E402
from gws.phase_a1.run_gate05_detection import RUN_ID as MOVES_RUN_ID  # noqa: E402
from gws.phase_a1.run_gate05_detection import bench_map, load_pilot   # noqa: E402
from gws.phase_a1.run_gate05_transfer import auc_fit_score            # noqa: E402
from gws.phase_a1.series_guard import assert_series_hash              # noqa: E402
from gws.phase_a2.feature_matrix import build_feature_matrix          # noqa: E402
from gws.phase_a3.univariate import univariate_screen                 # noqa: E402

SEED = 20260719
EVID = pathlib.Path(__file__).resolve().parents[2] / "phases" / "gate05_evidence"


def band(scores, ci=0.95):
    s = np.sort(np.asarray(scores, float))
    return float(s[int((1 - ci) / 2 * len(s))]), \
        float(s[min(len(s) - 1, int((1 + ci) / 2 * len(s)))])


def era_of(dd):
    s = str(dd)[:10]
    return ("pre1990" if s < "1990-01-01" else "1990s" if s < "2000-01-01"
            else "2000s" if s < "2010-01-01" else "2010s")


def analyze(pts, fm, label_col="y"):
    y = pts[label_col].to_numpy()
    t = pts["event_date"].to_numpy()
    tk = pts["ticker_id"].to_numpy()
    X = fm.to_numpy(float)
    real = auc_fit_score(X, y, t)
    sh = band([auc_fit_score(X, shuffle_labels(y, SEED + i), t) for i in range(25)])
    shifted = auc_fit_score(X, shift_labels_within_ticker(y, tk, 5), t)
    return {"n": len(pts), "pos": int(y.sum()), "auc": real, "shuffle": sh,
            "shifted": shifted, "deleak_clean": bool(shifted <= sh[1] + 1e-9)}


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    pilot = load_pilot()
    strat_ids = [int(r["entity_id"]) for r in pilot if r["kind"] == "stratified"]
    bench = bench_map()

    series, date_idx, bench_by_ticker, dates_by = {}, {}, {}, {}
    for eid in strat_ids:
        s = load_series(conn, eid)
        if s is None:
            continue
        d, o, h, lo, c, v = s
        assert_series_hash(conn, MOVES_RUN_ID, eid, d)
        series[eid] = {"close": c, "high": h, "low": lo, "volume": v}
        date_idx[eid] = {dd: i for i, dd in enumerate(d)}
        dates_by[eid] = d
        bench_by_ticker[eid] = np.array([bench.get(dd, np.nan) for dd in d])

    mc = pd.DataFrame(conn.execute("SELECT * FROM gws.market_context").fetchall())
    mc = mc.set_index("date").astype(float)

    def event_frame(run_id, families=None):
        q = "SELECT ticker_id, event_date, family, variant_tag, outcome FROM " \
            "gws.anchor_events WHERE run_id=%s AND outcome IN ('winner','failed')"
        args = [run_id]
        if families:
            q += " AND family = ANY(%s)"; args.append(list(families))
        ev = pd.DataFrame(conn.execute(q, args).fetchall())
        if ev.empty:
            return ev
        ev["idx0"] = [date_idx.get(tk, {}).get(d)
                      for tk, d in zip(ev["ticker_id"], ev["event_date"])]
        ev = ev.dropna(subset=["idx0"]).astype({"idx0": int})
        ev["as_of_index"] = ev["idx0"] - 1                      # features at B−1
        ev = ev[ev["as_of_index"] >= 252].reset_index(drop=True)
        ev["y"] = (ev["outcome"] == "winner").astype(int)
        return ev

    def features_for(ev):
        fm = build_feature_matrix(ev, series, bench_by_ticker=bench_by_ticker,
                                  include_generic=True, vectorized=True, n_jobs=16)
        ctx = []
        for tk, i in zip(ev["ticker_id"], ev["as_of_index"]):
            d1 = dates_by[tk][i]
            row = mc.loc[d1] if d1 in mc.index else None
            b = bench_by_ticker[tk]
            cclose = series[tk]["close"]
            dc = np.nan
            lo_w = max(0, i - 63)
            if i - lo_w > 25 and np.isfinite(b[lo_w:i]).all():
                rets = pd.Series(b[lo_w:i + 1]).pct_change(21).to_numpy()
                j = int(np.nanargmin(rets))
                if rets[j] < 0:
                    j0 = lo_w + j - 21
                    dc = (cclose[lo_w + j] / cclose[j0] - 1) / rets[j]
            ctx.append({
                "ctx_spx_vs_200d": row["spx_vs_200d"] if row is not None else np.nan,
                "ctx_spx_vs_50d": row["spx_vs_50d"] if row is not None else np.nan,
                "ctx_spx_dist_52w_high": row["spx_dist_52w_high"] if row is not None else np.nan,
                "ctx_spx_ret_std_21": row["spx_ret_std_21"] if row is not None else np.nan,
                "ctx_breadth_pct_above_5d": row["breadth_pct_above_5d"] if row is not None else np.nan,
                "ctx_breadth_pct_above_200d": row["breadth_pct_above_200d"] if row is not None else np.nan,
                "ctx_downside_capture_63": dc})
        return pd.concat([fm, pd.DataFrame(ctx, index=fm.index)], axis=1)

    out = {"spec": "B_ANCHOR3 36a13da", "seed": SEED, "per_family": {}}
    ev_all = event_frame(RUN)
    print(f"events in contrast: {len(ev_all)}", flush=True)

    for fam in "ABCDEF":
        ev = ev_all[ev_all["family"] == fam].reset_index(drop=True)
        if len(ev) < 200:
            out["per_family"][fam] = {"n": len(ev), "underpowered": True}
            continue
        fm = features_for(ev)
        res = analyze(ev, fm)
        uni = univariate_screen(fm, ev["y"].to_numpy(),
                                cluster_ids=ev["ticker_id"].to_numpy())
        res["n_sig"] = int(uni["significant"].sum())
        res["top10"] = uni.head(10)[["feature", "cohens_d", "qvalue"]].to_dict("records")
        res["era_auc"] = {}
        eras = ev["event_date"].map(era_of)
        for e in ("pre1990", "1990s", "2000s", "2010s"):
            m = (eras == e).to_numpy()
            if m.sum() >= 200 and len(set(ev["y"][m])) == 2:
                res["era_auc"][e] = auc_fit_score(fm[m].to_numpy(float),
                                                  ev["y"].to_numpy()[m],
                                                  ev["event_date"].to_numpy()[m])
        out["per_family"][fam] = res
        print(f"[{fam}] n={res['n']} pos={res['pos']} AUC={res['auc']:.3f} "
              f"shuffle_hi={res['shuffle'][1]:.3f} shifted={res['shifted']:.3f} "
              f"deleak={'OK' if res['deleak_clean'] else 'FLAG'} sig={res['n_sig']} "
              f"era={ {k: round(v, 3) for k, v in res['era_auc'].items()} }", flush=True)

    print("robustness (Family A variants):", flush=True)
    prim_dir = out["per_family"]["A"]["auc"] > out["per_family"]["A"]["shuffle"][1] + 0.05
    agree = []
    for key, val in [("a_depth", 0.25), ("a_depth", 0.45), ("a_vol", 1.25),
                     ("a_vol", 2.0), ("a_win", 40), ("a_win", 90)]:
        ev = event_frame(f"{RUN}:{key}={val}", families=["A"])
        if len(ev) < 200:
            continue
        fm = features_for(ev)
        r = analyze(ev, fm)
        d = r["auc"] > r["shuffle"][1] + 0.05
        agree.append(d == prim_dir)
        out.setdefault("a_variants", {})[f"{key}={val}"] = {"auc": r["auc"],
                                                            "n": r["n"], "dir": bool(d)}
        print(f"  {key}={val}: AUC={r['auc']:.3f} n={r['n']}", flush=True)

    a = out["per_family"]["A"]
    sep = a["auc"] > a["shuffle"][1] + 0.05
    weak = a["shuffle"][1] < a["auc"] <= a["shuffle"][1] + 0.05
    robust_ok = (sum(agree) > len(agree) / 2) if agree else False
    cell = ("P-D" if not a["deleak_clean"] else
            "P-A" if sep and robust_ok else
            "P-B" if weak or (sep and not robust_ok) else "P-C")
    out["decision"] = {"cell": cell, "family_A_auc": a["auc"],
                       "deleak_clean": a["deleak_clean"],
                       "variants_agreeing": f"{sum(agree)}/{len(agree)}"}
    print(f"\nDECISION MATRIX (Family A): cell {cell} — Scott signs the cell.", flush=True)

    with (EVID / "b_anchor3_results.json").open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("evidence -> b_anchor3_results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
