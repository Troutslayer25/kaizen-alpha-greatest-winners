"""Gate 0.5 pilot — steps 5–7: frozen-net features, univariate (ticker-clustered),
negative-control harness, and the §12.1 transfer/stationarity experiment.

Discovery frame: cases = resolved trail_6 troughs, controls = pre-committed MINIMAL
construction (same-date pilot-internal); liquidity construction is the robustness label.
Features at each point's own bar (PIT by construction; outcome quarantine enforced at the
matrix choke point). Inference: cluster-robust by ticker. ADVERSARIAL names are excluded
from ALL transfer metrics (pre-commit) — they are pipeline stress only.

§12.1 (all pre-committed): primary era split at 2010-01-01 (robustness 2000-01-01), run
per THESIS_CLASS family set (emotional vs structural, registered in feature_catalog
BEFORE this ran); evidence metrics = (a) sign agreement of univariate effect directions
train->test, (b) Spearman rank correlation of effect sizes, (c) OOS AUC of a pooled simple
model (standardized logistic) on the test window vs within-window baseline; negative-null
band from the shuffle harness. Artifacts -> phases/gate05_evidence/.

    python -m gws.phase_a1.run_gate05_transfer
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib

from gws.common.negative_controls import (negative_control_report,       # noqa: E402
                                          negative_control_verdicts)
from gws.phase_a1.detect_driver import detect_moves_for_ticker           # noqa: E402
from gws.phase_a1.run_gate05_detection import SCALES, bench_map, load_pilot  # noqa: E402
from gws.phase_a2.feature_catalog import thesis_class_of                 # noqa: E402
from gws.phase_a2.feature_matrix import build_feature_matrix             # noqa: E402
from gws.phase_a3.univariate import univariate_screen                    # noqa: E402

RUN_ID = "gate05_pilot"
SEED = 20260719
SPLITS = {"primary_2010": "2010-01-01", "robustness_2000": "2000-01-01"}
EVIDENCE_DIR = pathlib.Path(__file__).resolve().parents[2] / "phases" / "gate05_evidence"


def auc_fit_score(X, y, t):
    """Simple pooled model score: standardized logistic, era-ordered 70/30 OOS AUC."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    order = np.argsort(np.asarray(t))
    X, y = np.asarray(X, float)[order], np.asarray(y)[order]
    cut = int(0.7 * len(y))
    if len(set(y[:cut])) < 2 or len(set(y[cut:])) < 2:
        return 0.5
    mu, sd = np.nanmean(X[:cut], 0), np.nanstd(X[:cut], 0) + 1e-9
    Xs = np.nan_to_num((X - mu) / sd)
    m = LogisticRegression(max_iter=1000).fit(Xs[:cut], y[:cut])
    return float(roc_auc_score(y[cut:], m.predict_proba(Xs[cut:])[:, 1]))


def pooled_auc(fm, y, train_mask, feature_cols, dates):
    """Train on the train-era rows, score AUC on test-era rows (and a within-train temporal
    70/30 baseline — the cut MUST be in date order; frame order interleaves cases/controls
    and produced single-class tails on the first run, 2026-07-24)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    X = fm[feature_cols].to_numpy(float)
    mu = np.nanmean(X[train_mask], 0)
    sd = np.nanstd(X[train_mask], 0) + 1e-9
    Xs = np.nan_to_num((X - mu) / sd)
    ytr, yte = y[train_mask], y[~train_mask]
    if len(set(ytr)) < 2 or len(set(yte)) < 2:
        return np.nan, np.nan
    idx = np.where(train_mask)[0]
    idx = idx[np.argsort(np.asarray(dates)[idx], kind="mergesort")]
    cut = int(0.7 * len(idx))
    within = np.nan
    if len(set(y[idx[:cut]])) >= 2 and len(set(y[idx[cut:]])) >= 2:
        m_oos = LogisticRegression(max_iter=1000).fit(Xs[idx[:cut]], y[idx[:cut]])
        within = float(roc_auc_score(y[idx[cut:]], m_oos.predict_proba(Xs[idx[cut:]])[:, 1]))
    m = LogisticRegression(max_iter=1000).fit(Xs[train_mask], ytr)
    cross = float(roc_auc_score(yte, m.predict_proba(Xs[~train_mask])[:, 1]))
    return cross, within


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    t0 = time.perf_counter()
    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    EVIDENCE_DIR.mkdir(exist_ok=True)
    pilot = load_pilot()
    kind = {int(r["entity_id"]): r["kind"] for r in pilot}
    bench = bench_map()

    print("loading cleaned series for 300 names ...", flush=True)
    from gws.phase_a1.series_guard import assert_series_hash  # M3 composition guard
    series, date_idx, bench_by_ticker = {}, {}, {}
    for r in pilot:
        eid = int(r["entity_id"])
        dates, close, high, low, volume, _ = detect_moves_for_ticker(
            conn, eid, source="norgate", scales=SCALES)
        if not dates:
            continue
        assert_series_hash(conn, RUN_ID, eid, dates)
        series[eid] = {"close": close, "high": high, "low": low, "volume": volume}
        date_idx[eid] = {d: i for i, d in enumerate(dates)}
        bench_by_ticker[eid] = np.array([bench.get(d, np.nan) for d in dates])

    cases = pd.DataFrame(conn.execute(
        "SELECT m.move_id, m.ticker_id, m.start_date AS date FROM gws.moves m "
        "WHERE m.run_id=%s AND m.scale='trail_6' AND NOT m.is_open", (RUN_ID,)).fetchall())
    ctl = pd.DataFrame(conn.execute(
        "SELECT matched_move_id, ticker_id, date, match_liquidity_bucket "
        "FROM gws.matched_controls").fetchall())

    frames = {}
    for tag in ("minimal", "liquidity"):
        c = ctl[ctl["match_liquidity_bucket"].isna()] if tag == "minimal" \
            else ctl[ctl["match_liquidity_bucket"].notna()]
        pts = pd.concat([
            cases.assign(label=1)[["ticker_id", "date", "label"]],
            c.assign(label=0)[["ticker_id", "date", "label"]]], ignore_index=True)
        pts["as_of_index"] = [date_idx.get(tk, {}).get(d)
                              for tk, d in zip(pts["ticker_id"], pts["date"])]
        pts = pts.dropna(subset=["as_of_index"]).reset_index(drop=True)
        pts["as_of_index"] = pts["as_of_index"].astype(int)
        pts = pts[pts["ticker_id"].isin(series)].reset_index(drop=True)
        frames[tag] = pts
        print(f"points[{tag}]: {len(pts)} ({int(pts['label'].sum())} cases)", flush=True)

    t_feat = time.perf_counter()
    fms = {tag: build_feature_matrix(pts, series, bench_by_ticker=bench_by_ticker,
                                     include_generic=True, vectorized=True, n_jobs=16)
           for tag, pts in frames.items()}
    print(f"feature matrices built in {time.perf_counter() - t_feat:.0f}s: "
          f"{ {t: f.shape for t, f in fms.items()} }", flush=True)

    evidence = {"run_id": RUN_ID, "seed": SEED}

    # ---- step 5: univariate, ticker-clustered, both constructions ----------------------
    for tag in ("minimal", "liquidity"):
        pts, fm = frames[tag], fms[tag]
        uni = univariate_screen(fm, pts["label"].to_numpy(),
                                cluster_ids=pts["ticker_id"].to_numpy())
        uni.to_csv(EVIDENCE_DIR / f"univariate_{tag}.csv", index=False)
        n_sig = int(uni["significant"].sum())
        print(f"univariate[{tag}]: {n_sig}/{len(uni)} significant (BH)", flush=True)
        evidence[f"univariate_{tag}_significant"] = n_sig
        evidence[f"univariate_{tag}_features"] = len(uni)

    # ---- step 6: negative controls + PIT note ------------------------------------------
    pts, fm = frames["minimal"], fms["minimal"]
    strat = pts["ticker_id"].map(lambda e: kind.get(int(e))) == "stratified"
    # M2 guard (review): on a universe file without kind tags this mask is all-False and
    # steps 6-7 would silently run on ZERO rows — hard-fail instead.
    if not strat.any():
        raise RuntimeError("stratified mask selected 0 rows — universe source has no 'kind' "
                           "tags or none are 'stratified'; refusing to run steps 6-7 on an "
                           "empty subset (review M2)")
    Xnc = fm.loc[strat].to_numpy(float)
    ync = pts.loc[strat, "label"].to_numpy()
    tnc = pts.loc[strat, "date"].to_numpy()
    rep = negative_control_report(Xnc, ync, tnc, auc_fit_score,
                                  tickers=pts.loc[strat, "ticker_id"].to_numpy(),
                                  seed=SEED, n_null=25)
    verd = negative_control_verdicts(rep)
    print(f"negative controls: real={rep['real']:.3f} "
          f"shuffle_band=({rep['shuffle_null']['lo']:.3f},{rep['shuffle_null']['hi']:.3f}) "
          f"verdicts={verd}", flush=True)
    evidence["negative_controls"] = {"report": rep, "verdicts": verd}

    # ---- step 7: §12.1 transfer experiment ---------------------------------------------
    fam_cols = {"emotional": [], "structural": []}
    for col in fm.columns:
        tc = thesis_class_of(col)
        if tc in fam_cols:
            fam_cols[tc].append(col)
    print(f"thesis families: emotional={len(fam_cols['emotional'])} "
          f"structural={len(fam_cols['structural'])} of {fm.shape[1]} features", flush=True)

    transfer = {}
    y = pts["label"].to_numpy()
    for split_name, split_date in SPLITS.items():
        cut = pd.Timestamp(split_date).date()
        m_strat = strat.to_numpy()
        train = (pts["date"] < cut).to_numpy() & m_strat
        test = (pts["date"] >= cut).to_numpy() & m_strat
        res = {"n_train": int(train.sum()), "n_test": int(test.sum()),
               "train_pos": int(y[train].sum()), "test_pos": int(y[test].sum())}
        for fam, cols in fam_cols.items():
            ut = univariate_screen(fm.loc[train, cols], y[train],
                                   cluster_ids=pts.loc[train, "ticker_id"].to_numpy())
            ue = univariate_screen(fm.loc[test, cols], y[test],
                                   cluster_ids=pts.loc[test, "ticker_id"].to_numpy())
            mg = ut.merge(ue, on="feature", suffixes=("_tr", "_te"))
            mg = mg.dropna(subset=["cohens_d_tr", "cohens_d_te"])
            sign_agree = float((np.sign(mg["cohens_d_tr"]) ==
                                np.sign(mg["cohens_d_te"])).mean())
            from scipy.stats import spearmanr
            rho = float(spearmanr(mg["cohens_d_tr"], mg["cohens_d_te"]).statistic)
            sub = train | test
            cross, within = pooled_auc(fm[sub].reset_index(drop=True), y[sub],
                                       train[sub], cols, pts.loc[sub, "date"].to_numpy())
            res[fam] = {"sign_agreement": sign_agree, "spearman_effect": rho,
                        "oos_auc_cross_era": cross, "oos_auc_within_train": within,
                        "n_features_compared": int(len(mg))}
            print(f"  {split_name} {fam:10}: sign={sign_agree:.2f} rho={rho:.2f} "
                  f"AUC cross={cross:.3f} within={within:.3f} (n={len(mg)})", flush=True)
        transfer[split_name] = res
    evidence["transfer"] = transfer
    evidence["wall_seconds"] = round(time.perf_counter() - t0, 1)

    with (EVIDENCE_DIR / "gate05_evidence.json").open("w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, default=str)
    print(f"\nevidence written to {EVIDENCE_DIR} in {evidence['wall_seconds']}s total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
