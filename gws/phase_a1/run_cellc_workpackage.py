"""Cell C work package, AS AMENDED (phases/CELLC_WORKPACKAGE_PRECOMMIT.md, 65e5582):
W1 re-scoped de-leak + W2' REWIND analysis. W2 trough-prediction bar WITHDRAWN per
Scott's intent correction; W3 deferred; B-anchor-3 promoted (own pre-commit next).

W1  — shift@5 de-leak on the location-residualized feature set, forward frame.
W2' — cases (trail_6 troughs) vs persisted minimal same-date controls, features at
      T-0 (reference) / T-5 / T-21 / T-63 bars BEFORE the anchor date. Was the move
      visible being born, without standing on the low?

    python -m gws.phase_a1.run_cellc_workpackage
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

from gws.common.negative_controls import shift_labels_within_ticker, shuffle_labels  # noqa: E402
from gws.phase_a1.detect_driver import detect_moves_for_ticker           # noqa: E402
from gws.phase_a1.run_gate05_detection import (RUN_ID, SCALES, bench_map,  # noqa: E402
                                               load_pilot)
from gws.phase_a1.run_gate05_transfer import auc_fit_score               # noqa: E402
from gws.phase_a1.series_guard import assert_series_hash                 # noqa: E402
from gws.phase_a2.feature_catalog import family_of                       # noqa: E402
from gws.phase_a2.feature_matrix import build_feature_matrix             # noqa: E402
from gws.phase_a3.univariate import univariate_screen                    # noqa: E402

SEED = 20260719
K = 20
OFFSETS = (0, 5, 21, 63)
EVID = pathlib.Path(__file__).resolve().parents[2] / "phases" / "gate05_evidence"
ERA_CAP = "2022-01-01"


def band(scores, ci=0.95):
    s = np.sort(np.asarray(scores, float))
    return float(s[int((1 - ci) / 2 * len(s))]), \
        float(s[min(len(s) - 1, int((1 + ci) / 2 * len(s)))])


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    pilot = load_pilot()
    strat_ids = [int(r["entity_id"]) for r in pilot if r["kind"] == "stratified"]
    bench = bench_map()

    series, date_idx, bench_by_ticker = {}, {}, {}
    for eid in strat_ids:
        dates, close, high, low, volume, _ = detect_moves_for_ticker(
            conn, eid, source="norgate", scales=SCALES)
        if not dates:
            continue
        assert_series_hash(conn, RUN_ID, eid, dates)
        series[eid] = {"close": close, "high": high, "low": low, "volume": volume}
        date_idx[eid] = {d: i for i, d in enumerate(dates)}
        bench_by_ticker[eid] = np.array([bench.get(d, np.nan) for d in dates])

    out: dict = {"spec": "CELLC_WORKPACKAGE_PRECOMMIT as amended 65e5582", "seed": SEED}

    # ---- W1: re-scoped de-leak on the forward frame -------------------------------------
    pts = pd.DataFrame(conn.execute(
        "SELECT ticker_id, date, label FROM gws.setup_labels "
        "WHERE forward_window_k=%s AND ticker_id = ANY(%s)", (K, strat_ids)).fetchall())
    assert str(pts["date"].max()) < ERA_CAP
    pts["as_of_index"] = [date_idx.get(tk, {}).get(d)
                          for tk, d in zip(pts["ticker_id"], pts["date"])]
    pts = (pts.dropna(subset=["as_of_index"]).astype({"as_of_index": int})
              .sort_values(["ticker_id", "as_of_index"]).reset_index(drop=True))
    fm = build_feature_matrix(pts, series, bench_by_ticker=bench_by_ticker,
                              include_generic=True, vectorized=True, n_jobs=16)
    res_cols = [c for c in fm.columns if family_of(c) != "location"]
    X_res = fm[res_cols].to_numpy(float)
    y = pts["label"].astype(int).to_numpy()
    t = pts["date"].to_numpy()
    tickers = pts["ticker_id"].to_numpy()
    sh = band([auc_fit_score(X_res, shuffle_labels(y, SEED + i), t) for i in range(25)])
    real_res = auc_fit_score(X_res, y, t)
    shifted_res = auc_fit_score(X_res, shift_labels_within_ticker(y, tickers, 5), t)
    w1_pass = bool(shifted_res <= sh[1] + 1e-9 and real_res > sh[1] + 0.05)
    out["w1"] = {"real_res": real_res, "shuffle": sh, "shifted_res": shifted_res,
                 "pass": w1_pass, "n_features_res": len(res_cols)}
    print(f"W1: real_res={real_res:.3f} shuffle=({sh[0]:.3f},{sh[1]:.3f}) "
          f"shifted_res={shifted_res:.3f} -> {'PASS' if w1_pass else 'FAIL'}", flush=True)

    # ---- W2': rewind analysis -----------------------------------------------------------
    cases = pd.DataFrame(conn.execute(
        "SELECT ticker_id, start_date AS date FROM gws.moves WHERE run_id=%s "
        "AND scale='trail_6' AND NOT is_open AND ticker_id = ANY(%s)",
        (RUN_ID, strat_ids)).fetchall())
    ctrls = pd.DataFrame(conn.execute(
        "SELECT mc.ticker_id, mc.date FROM gws.matched_controls mc "
        "JOIN gws.moves m ON m.move_id = mc.matched_move_id "
        "WHERE mc.match_liquidity_bucket IS NULL AND m.ticker_id = ANY(%s) "
        "AND mc.ticker_id = ANY(%s)", (strat_ids, strat_ids)).fetchall())
    base = pd.concat([cases.assign(label=1), ctrls.assign(label=0)], ignore_index=True)
    base["idx0"] = [date_idx.get(tk, {}).get(d)
                    for tk, d in zip(base["ticker_id"], base["date"])]
    base = base.dropna(subset=["idx0"]).astype({"idx0": int}).reset_index(drop=True)
    print(f"W2' frame: {int(base['label'].sum())} cases, "
          f"{int((base['label'] == 0).sum())} controls", flush=True)

    out["w2_rewind"] = {}
    for off in OFFSETS:
        p = base.copy()
        p["as_of_index"] = p["idx0"] - off
        p = p[p["as_of_index"] >= 252].reset_index(drop=True)
        f = build_feature_matrix(p, series, bench_by_ticker=bench_by_ticker,
                                 include_generic=True, vectorized=True, n_jobs=16)
        yb = p["label"].to_numpy()
        tb = p["date"].to_numpy()
        Xr = f[res_cols].to_numpy(float)
        shb = band([auc_fit_score(Xr, shuffle_labels(yb, SEED + i), tb) for i in range(15)])
        auc_r = auc_fit_score(Xr, yb, tb)
        auc_f = auc_fit_score(f.to_numpy(float), yb, tb)
        uni = univariate_screen(f[res_cols], yb, cluster_ids=p["ticker_id"].to_numpy())
        top = uni.head(10)[["feature", "cohens_d", "qvalue"]].to_dict("records")
        out["w2_rewind"][f"T-{off}"] = {
            "n": len(p), "auc_res": auc_r, "auc_full": auc_f, "shuffle": shb,
            "n_sig": int(uni["significant"].sum()), "top10": top}
        print(f"W2'[T-{off:>2}]: n={len(p):>6} auc_res={auc_r:.3f} auc_full={auc_f:.3f} "
              f"shuffle_hi={shb[1]:.3f} sig={int(uni['significant'].sum())}/{len(uni)}",
              flush=True)

    born_bar = out["w2_rewind"]["T-21"]["auc_res"] > out["w2_rewind"]["T-21"]["shuffle"][1] + 0.05
    out["reading"] = {"visible_being_born_T21": bool(born_bar)}
    print(f"\nPRE-COMMITTED READING — visible being born (T-21 bar): "
          f"{'YES' if born_bar else 'NO'}")

    with (EVID / "cellc_workpackage.json").open("w", encoding="utf-8") as fjson:
        json.dump(out, fjson, indent=2, default=str)
    print("evidence -> cellc_workpackage.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
