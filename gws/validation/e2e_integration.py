"""End-to-end synthetic integration harness — the dress rehearsal for Gate 0.5.

Unit tests prove COMPONENTS; this proves the SEAMS. It wires the real analytical spine on a
synthetic panel with a planted signal and asserts the whole pipeline behaves:

  generate (planted moves + planted pre-move signal + a null feature)
    -> detect_moves_multiscale            (does detection recover the planted troughs?)
    -> build_setup_labels                 (labeling from the primary-scale moves)
    -> build_feature_matrix               (real feature functions at the labeled points)
    -> univariate_screen (ticker-clustered)  (does it RECOVER the planted signal + reject the null?)
    -> shuffled-label control             (does the planted signal correctly VANISH under a null?)

If the planted signal is recovered, the null feature is not significant, and the signal vanishes
under shuffled labels, the integration is sound. This is the single highest-value pre-data check:
it catches the wiring bugs that only appear when the real components meet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from gws.phase_a1.labeling import build_setup_labels
from gws.phase_a1.move_detector_mfe import detect_moves_multiscale
from gws.phase_a2.feature_matrix import build_feature_matrix
from gws.phase_a3.univariate import univariate_screen
from gws.synthetic.generate import generate_panel


def run_e2e(seed: int = 0, n_tickers: int = 15, n_days: int = 1000, primary_trail: float = 6.0,
            forward_k: int = 20, trough_tol: int = 8) -> dict:
    panel, truth = generate_panel(n_tickers, n_days, seed=seed, planted_per_ticker=3)

    series_by_ticker, moves_by_ticker = {}, {}
    ps_by_ticker, nf_by_ticker = {}, {}
    detected = {}
    for tk, g in panel.groupby("ticker_id"):
        g = g.sort_values("date")
        close = g["close"].to_numpy(float)
        series_by_ticker[tk] = {"close": close, "high": g["high"].to_numpy(float),
                                "low": g["low"].to_numpy(float), "volume": g["volume"].to_numpy(float)}
        ps_by_ticker[tk] = g["planted_signal"].to_numpy(float)
        nf_by_ticker[tk] = g["null_feature"].to_numpy(float)
        moves = detect_moves_multiscale(series_by_ticker[tk]["high"], series_by_ticker[tk]["low"],
                                        close).get(primary_trail, [])
        moves_by_ticker[tk] = moves
        detected[tk] = sorted(m.trough_idx for m in moves)

    # detection recall vs planted troughs
    hits = total = 0
    for _, r in truth.iterrows():
        total += 1
        d = detected.get(r["ticker_id"], [])
        hits += any(abs(t - r["trough_day"]) <= trough_tol for t in d)
    recall = hits / total if total else float("nan")

    labels_df = build_setup_labels(moves_by_ticker, n_days, forward_k, min_index=252)
    points = labels_df[["ticker_id", "as_of_index"]].reset_index(drop=True)
    labels = labels_df["label"].to_numpy().astype(int)
    tickers = labels_df["ticker_id"].to_numpy()

    fm = build_feature_matrix(points, series_by_ticker, include_generic=False, dtype=np.float64)
    # attach the panel's planted (predictive) + null features at each labeled point
    fm = fm.reset_index(drop=True)
    fm["planted_signal"] = [ps_by_ticker[t][i] for t, i in zip(points["ticker_id"], points["as_of_index"])]
    fm["null_feature"] = [nf_by_ticker[t][i] for t, i in zip(points["ticker_id"], points["as_of_index"])]

    screen = univariate_screen(fm, labels, cluster_ids=tickers)
    shuffled = univariate_screen(fm, np.random.default_rng(seed + 1).permutation(labels),
                                 cluster_ids=tickers)

    def _sig(df, feat):
        row = df[df["feature"] == feat]
        return bool(row["significant"].iloc[0]) if len(row) else False

    return {
        "detection_recall": recall,
        "n_positive": int(labels.sum()), "n_points": len(labels),
        "planted_significant": _sig(screen, "planted_signal"),
        "null_significant": _sig(screen, "null_feature"),
        "planted_significant_under_shuffle": _sig(shuffled, "planted_signal"),
    }
