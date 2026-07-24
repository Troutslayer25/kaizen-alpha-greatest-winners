"""A1 opening act — T2 settling package (pre-committed in the A1 addendum, 2026-07-24).

Runs BOTH pre-committed bars on the FORWARD `setup_labels` (deployment) frame, stratified
pilot names only, features at each sampled point's own bar (the label looks forward; the
features cannot):

  B-anchor-1 (de-leak):  negative-control harness on the forward frame. PASS iff the
      within-ticker label-shift control falls INSIDE the shuffle-null band while the real
      score stays materially above it. FAIL -> premise-level review (Cell C).
  B-anchor-2 (differential): the frozen PHASE_A3_TRANSFER_PRECOMMIT instrument
      (gws/regime/transfer_test.py: symmetric era-relative normalization, transfer RATIO,
      >=3 ordered era pairs, invariance_supported majority rule) with the anchor variables
      (location family) REMOVED from the structural arm. NOT SUPPORTED -> operative cell B.

Era bins (pre-committed): pre-1990 / 1990-1999 / 2000-2009 / 2010-2021 -> 12 ordered pairs.
Artifacts -> phases/gate05_evidence/anchor_settling.json. Composition is hash-guarded.

    python -m gws.phase_a1.run_a1_anchor_settling
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

from gws.common.negative_controls import (negative_control_report,       # noqa: E402
                                          negative_control_verdicts)
from gws.phase_a1.detect_driver import detect_moves_for_ticker           # noqa: E402
from gws.phase_a1.run_gate05_detection import (RUN_ID, SCALES, bench_map,  # noqa: E402
                                               load_pilot)
from gws.phase_a1.run_gate05_transfer import auc_fit_score               # noqa: E402
from gws.phase_a1.series_guard import assert_series_hash                 # noqa: E402
from gws.phase_a2.feature_catalog import family_of, thesis_class_of      # noqa: E402
from gws.phase_a2.feature_matrix import build_feature_matrix             # noqa: E402
from gws.regime.transfer_test import (invariance_supported,              # noqa: E402
                                      regime_relative_normalize, transfer_distribution)

SEED = 20260719
K = 20
ERA_EDGES = [(None, "1990-01-01", "pre1990"), ("1990-01-01", "2000-01-01", "e1990s"),
             ("2000-01-01", "2010-01-01", "e2000s"), ("2010-01-01", None, "e2010s")]
EVIDENCE = pathlib.Path(__file__).resolve().parents[2] / "phases" / "gate05_evidence"


def era_of(d) -> str:
    d = pd.Timestamp(d).date()
    for lo, hi, name in ERA_EDGES:
        if (lo is None or str(d) >= lo) and (hi is None or str(d) < hi):
            return name
    return "?"


def pair_fit_score(X_tr, y_tr, X_te, y_te) -> float:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    mu, sd = np.nanmean(X_tr, 0), np.nanstd(X_tr, 0) + 1e-9
    m = LogisticRegression(max_iter=1000).fit(np.nan_to_num((X_tr - mu) / sd), y_tr)
    return float(roc_auc_score(y_te, m.predict_proba(np.nan_to_num((X_te - mu) / sd))[:, 1]))


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    pilot = load_pilot()
    strat_ids = [int(r["entity_id"]) for r in pilot if r["kind"] == "stratified"]
    bench = bench_map()

    print("rebuilding hash-guarded series ...", flush=True)
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

    pts = pd.DataFrame(conn.execute(
        "SELECT ticker_id, date, label FROM gws.setup_labels "
        "WHERE forward_window_k=%s AND ticker_id = ANY(%s)", (K, strat_ids)).fetchall())
    pts["as_of_index"] = [date_idx.get(tk, {}).get(d)
                          for tk, d in zip(pts["ticker_id"], pts["date"])]
    pts = pts.dropna(subset=["as_of_index"]).reset_index(drop=True)
    pts["as_of_index"] = pts["as_of_index"].astype(int)
    pts["label"] = pts["label"].astype(int)
    pts["era"] = pts["date"].map(era_of)
    print(f"forward-frame points: {len(pts)} ({pts['label'].mean():.1%} positive); "
          f"era counts: {pts['era'].value_counts().to_dict()}", flush=True)

    fm = build_feature_matrix(pts, series, bench_by_ticker=bench_by_ticker,
                              include_generic=True, vectorized=True, n_jobs=16)
    y = pts["label"].to_numpy()
    t = pts["date"].to_numpy()
    tickers = pts["ticker_id"].to_numpy()
    era = pts["era"].to_numpy()

    # ---- B-anchor-1: de-leak on the forward frame ---------------------------------------
    X_all = fm.to_numpy(float)
    rep = negative_control_report(X_all, y, t, auc_fit_score, tickers=tickers,
                                  seed=SEED, n_null=25)
    verd = negative_control_verdicts(rep)
    b1_pass = bool(rep["shifted_within_ticker"] <= rep["shuffle_null"]["hi"] + 1e-9
                   and rep["real"] > rep["shuffle_null"]["hi"] + 0.05)
    print(f"B-anchor-1: real={rep['real']:.3f} "
          f"shuffle=({rep['shuffle_null']['lo']:.3f},{rep['shuffle_null']['hi']:.3f}) "
          f"shifted={rep['shifted_within_ticker']:.3f} verdicts={verd} "
          f"-> {'PASS' if b1_pass else 'FAIL'}", flush=True)

    # ---- B-anchor-2: frozen A3 instrument, anchor vars out of the structural arm --------
    emotional = [c for c in fm.columns if thesis_class_of(c) == "emotional"]
    structural = [c for c in fm.columns if thesis_class_of(c) == "structural"
                  and family_of(c) != "location"]
    print(f"arms: emotional={len(emotional)} structural(minus location)={len(structural)}",
          flush=True)

    def era_normalized(cols):
        Xn = np.column_stack([regime_relative_normalize(fm[c].to_numpy(float), era)
                              for c in cols])
        return np.nan_to_num(Xn)

    results = {}
    for arm, cols in (("emotional", emotional), ("structural", structural)):
        results[arm] = transfer_distribution(pair_fit_score, era_normalized(cols), y, era,
                                             seed=SEED)
        print(f"  {arm}: median ratio={results[arm]['median']:.3f} "
              f"n_pairs={results[arm]['n_pairs']}", flush=True)
    pairs = sorted(set(results["emotional"]["pairwise"]) & set(results["structural"]["pairwise"]))
    verdict = invariance_supported(
        [results["emotional"]["pairwise"][p] for p in pairs],
        [results["structural"]["pairwise"][p] for p in pairs])
    print(f"B-anchor-2 invariance_supported: {verdict}", flush=True)

    out = {"run_id": RUN_ID, "frame": "setup_labels_forward", "K": K, "seed": SEED,
           "n_points": len(pts), "b_anchor_1": {"report": rep, "verdicts": verd,
                                                "pass": b1_pass},
           "b_anchor_2": {"emotional": {str(k): v for k, v in
                                        results["emotional"]["pairwise"].items()},
                          "structural": {str(k): v for k, v in
                                         results["structural"]["pairwise"].items()},
                          "verdict": verdict}}
    with (EVIDENCE / "anchor_settling.json").open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)

    print(f"\nSETTLING RESULT: B-anchor-1 {'PASS' if b1_pass else 'FAIL'}; "
          f"B-anchor-2 {'SUPPORTED' if verdict['supported'] else 'NOT SUPPORTED'} "
          f"(emotional wins {verdict['emotional_wins']}/{verdict['n_pairs']}, "
          f"medians e={verdict['emotional_median']:.3f} s={verdict['structural_median']:.3f})")
    print("Pre-committed reading: B1 FAIL -> Cell C review; B1 PASS + B2 NOT SUPPORTED -> "
          "operative cell B; B1 PASS + B2 SUPPORTED -> premise alive, A-provisional may firm "
          "(Scott rules).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
